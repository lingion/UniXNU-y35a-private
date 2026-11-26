// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read-only IOBlockStorageDevice for the Y35A removable TF controller.
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IOLib.h>
#include <IOKit/storage/IOBlockStorageDevice.h>
#include <libkern/c++/OSData.h>

#include "SdCardBus.h"

extern "C" {
volatile uint32_t native_sdcard_probe_bound = 0;
volatile uint32_t native_sdcard_started = 0;
volatile uint32_t native_sdcard_ready = 0;
volatile uint32_t native_sdcard_card_detect_unbound = 1;
volatile uint32_t native_sdcard_gpt_ok = 0;
volatile uint64_t native_sdcard_capacity = 0;
volatile uint64_t native_sdcard_sectors_read = 0;
}

namespace {
inline void writeBarrier() { __asm__ volatile("dsb oshst" ::: "memory"); }
}

class SdcardPorts {
 public:
  uintptr_t hc = 0, core = 0;

  uint32_t read32(unsigned r) const { return *reinterpret_cast<volatile uint32_t *>(hc + r); }
  uint16_t read16(unsigned r) const { return *reinterpret_cast<volatile uint16_t *>(hc + r); }
  uint8_t read8(unsigned r) const { return *reinterpret_cast<volatile uint8_t *>(hc + r); }
  void write32(unsigned r, uint32_t v) { *reinterpret_cast<volatile uint32_t *>(hc + r) = v; writeBarrier(); }
  void write16(unsigned r, uint16_t v) { *reinterpret_cast<volatile uint16_t *>(hc + r) = v; writeBarrier(); }
  void write8(unsigned r, uint8_t v) { *reinterpret_cast<volatile uint8_t *>(hc + r) = v; writeBarrier(); }
  uint32_t coreRead32(unsigned r) const { return *reinterpret_cast<volatile uint32_t *>(core + r); }
  void coreWrite32(unsigned r, uint32_t v) { *reinterpret_cast<volatile uint32_t *>(core + r) = v; writeBarrier(); }
  void delay() { IODelay(10); }

  // The SDHCI status path is the authoritative first probe. A TLMM consumer
  // is not linked yet; a missing card therefore fails through CMD0/CMD8 with
  // bounded timeouts rather than through guessed GPIO register semantics.
  bool cardPresent() const { return true; }

  void enableHostMode() {
    uint8_t host = read8(0x28), power = read8(0x29);
    uint16_t clock = read16(0x2c), host2 = read16(0x3e);
    uint32_t dll = read32(0x100), vendor = read32(0x10c);
    coreWrite32(0x78, coreRead32(0x78) | 1U);
    write32(0x38, 0);
    write16(0x2c, static_cast<uint16_t>(clock & ~4U));
    write32(0x10c, vendor);
    write8(0x28, host); write16(0x3e, host2); write32(0x100, dll); write8(0x29, power);
    uint32_t pending = coreRead32(0xdc);
    coreWrite32(0xe4, pending);
    uint32_t ack = coreRead32(0xe8);
    if (pending & 3U) ack |= 1U;
    if (pending & 12U) ack |= 4U;
    coreWrite32(0xe8, ack);
    for (unsigned i = 0; i != 50000 && !(read16(0x2c) & 2U); ++i) delay();
    write16(0x2c, clock);
  }

  uint32_t capacitySectors(const uint32_t response[4]) const {
    uint8_t csd[16];
    for (unsigned i = 0; i != 4; ++i) {
      uint32_t word = response[3 - i];
      csd[i * 4 + 0] = static_cast<uint8_t>(word >> 24);
      csd[i * 4 + 1] = static_cast<uint8_t>(word >> 16);
      csd[i * 4 + 2] = static_cast<uint8_t>(word >> 8);
      csd[i * 4 + 3] = static_cast<uint8_t>(word);
    }
    auto bits = [&csd](unsigned msb, unsigned lsb) -> uint64_t {
      uint64_t value = 0;
      for (unsigned bit = msb;; --bit) {
        value = (value << 1) | ((csd[(127 - bit) / 8] >> ((127 - bit) % 8)) & 1U);
        if (bit == lsb) break;
      }
      return value;
    };
    if (bits(127, 126) == 1) {
      uint64_t csize = bits(69, 48);
      return csize > 0xffffffffULL / 1024ULL ? 0 : static_cast<uint32_t>((csize + 1) * 1024);
    }
    uint64_t csize = bits(73, 62), mult = bits(49, 47), readLen = bits(83, 80);
    uint64_t bytes = (csize + 1) * (1ULL << (mult + 2)) * (1ULL << readLen);
    return bytes / 512 > 0xffffffffULL ? 0 : static_cast<uint32_t>(bytes / 512);
  }
};

class NativeSdcard : public IOBlockStorageDevice {
  OSDeclareDefaultStructors(NativeSdcard)
  SdcardPorts ports;
  SdCardBus<SdcardPorts> bus{ports};
  sdcard::Controller<SdCardBus<SdcardPorts>> card{bus};
  IOMemoryMap *hcMapping = nullptr, *coreMapping = nullptr;
  IOLock *gate = nullptr;
  uint8_t *staging = nullptr;
  uint32_t capacity = 0;
 public:
  IOService *probe(IOService *provider, SInt32 *score) override;
  bool start(IOService *provider) override;
  void stop(IOService *provider) override;
  void free() override;
  IOReturn doEjectMedia() override { return kIOReturnUnsupported; }
  IOReturn doFormatMedia(UInt64) override { return kIOReturnNotWritable; }
  UInt32 doGetFormatCapacities(UInt64 *, UInt32) const override { return 0; }
  char *getVendorString() override { return const_cast<char *>("Qualcomm"); }
  char *getProductString() override { return const_cast<char *>("Y35A TF card sdhc2"); }
  char *getRevisionString() override { return const_cast<char *>("sd-card-readonly-1"); }
  char *getAdditionalDeviceInfoString() override { return const_cast<char *>("MSM8916 SDHCI polling, removable TF"); }
  IOReturn reportBlockSize(UInt64 *value) override { *value = 512; return kIOReturnSuccess; }
  IOReturn reportEjectability(bool *value) override { *value = true; return kIOReturnSuccess; }
  IOReturn reportMaxValidBlock(UInt64 *value) override { *value = capacity ? capacity - 1 : 0; return kIOReturnSuccess; }
  IOReturn reportMediaState(bool *present, bool *changed) override {
    *present = card.ready(); if (changed) *changed = false; return kIOReturnSuccess;
  }
  IOReturn reportRemovability(bool *value) override { *value = true; return kIOReturnSuccess; }
  IOReturn reportWriteProtection(bool *value) override { *value = true; return kIOReturnSuccess; }
  IOReturn doSynchronizeCache() override { return card.ready() ? kIOReturnSuccess : kIOReturnNotReady; }
  IOReturn doSynchronize(UInt64, UInt64, IOOptionBits) override { return doSynchronizeCache(); }
  IOReturn getWriteCacheState(bool *value) override { *value = false; return kIOReturnSuccess; }
  IOReturn setWriteCacheState(bool) override { return kIOReturnUnsupported; }
  IOReturn doAsyncReadWrite(IOMemoryDescriptor *, UInt64, UInt64, IOStorageAttributes *, IOStorageCompletion *) override;
};

OSDefineMetaClassAndStructors(NativeSdcard, IOBlockStorageDevice)

IOService *NativeSdcard::probe(IOService *provider, SInt32 *score) {
  OSData *slot = OSDynamicCast(OSData, provider->getProperty("unixnu,slot"));
  OSData *compatible = OSDynamicCast(OSData, provider->getProperty("compatible"));
  if (!slot || slot->getLength() != 4 || *static_cast<const uint32_t *>(slot->getBytesNoCopy()) != 2 ||
      !compatible || compatible->getLength() != 15 ||
      memcmp(compatible->getBytesNoCopy(), "qcom,sdhci-msm", 15)) return nullptr;
  native_sdcard_probe_bound = 1;
  return IOBlockStorageDevice::probe(provider, score);
}

bool NativeSdcard::start(IOService *provider) {
  if (!IOBlockStorageDevice::start(provider)) return false;
  hcMapping = provider->mapDeviceMemoryWithIndex(0, kIOMapAnywhere | kIOMapInhibitCache);
  coreMapping = provider->mapDeviceMemoryWithIndex(1, kIOMapAnywhere | kIOMapInhibitCache);
  if (!hcMapping || hcMapping->getLength() < 0x11c || !coreMapping || coreMapping->getLength() < 0x800) return false;
  ports.hc = static_cast<uintptr_t>(hcMapping->getVirtualAddress());
  ports.core = static_cast<uintptr_t>(coreMapping->getVirtualAddress());
  gate = IOLockAlloc(); staging = static_cast<uint8_t *>(IOMalloc(65536));
  if (!gate || !staging) return false;
  ports.enableHostMode();
  if (!card.init()) return false;
  capacity = card.info().sectors;
  native_sdcard_capacity = capacity;
  IOLockLock(gate);
  bool first = card.readSectors(0, 1, staging);
  IOLockUnlock(gate);
  if (!first) return false;
  native_sdcard_gpt_ok = 1;
  native_sdcard_ready = 1;
  native_sdcard_started = 1;
  registerService();
  return true;
}

IOReturn NativeSdcard::doAsyncReadWrite(IOMemoryDescriptor *buffer, UInt64 block, UInt64 count,
                                        IOStorageAttributes *, IOStorageCompletion *completion) {
  if (!buffer || !completion || !completion->action || !count || block >= capacity ||
      count > capacity - block || buffer->getDirection() != kIODirectionIn)
    return kIOReturnBadArgument;
  UInt64 actual = 0; IOReturn result = kIOReturnNotReady;
  IOLockLock(gate);
  while (actual < count * 512) {
    UInt64 bytes = count * 512 - actual > 65536 ? 65536 : count * 512 - actual;
    if (!card.readSectors(static_cast<uint32_t>(block + actual / 512), static_cast<unsigned>(bytes / 512), staging)) {
      result = kIOReturnIOError; break;
    }
    if (buffer->writeBytes(actual, staging, bytes) != bytes) { result = kIOReturnIOError; break; }
    actual += bytes; native_sdcard_sectors_read += bytes / 512; result = kIOReturnSuccess;
  }
  IOLockUnlock(gate);
  completion->action(completion->target, completion->parameter, result, actual);
  return kIOReturnSuccess;
}

void NativeSdcard::stop(IOService *provider) {
  native_sdcard_ready = 0;
  if (gate) IOLockLock(gate);
  IOBlockStorageDevice::stop(provider);
  if (gate) IOLockUnlock(gate);
}

void NativeSdcard::free() {
  if (gate) { IOLockFree(gate); gate = nullptr; }
  if (staging) { IOFree(staging, 65536); staging = nullptr; }
  if (hcMapping) { hcMapping->release(); hcMapping = nullptr; }
  if (coreMapping) { coreMapping->release(); coreMapping = nullptr; }
  IOBlockStorageDevice::free();
}
