// SPDX-License-Identifier: BSD-2-Clause-Patent
// NativeSdcc — IOBlockStorageDevice over the MSM8916 sdhc1 (eMMC) controller,
// resuming the lk2nd-configured card (SPEC.md §3, Phase 1: resume + read +
// publish, write-refusing). The register transport is SdciCore.h's template,
// the identical code exercised by Test/sdcc_host.cpp under ASan/UBSan.
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IOLib.h>
#include <IOKit/storage/IOBlockStorageDevice.h>
#include <libkern/c++/OSData.h>
#include <libkern/crypto/sha2.h>
#include <kern/clock.h>

#include "PersistStore.h"
#include "SdciCore.h"

// Boot-time checkpoints (read via the proven fastboot staging / GDB observer
// path, same discipline as native_virtio_*): each records one SPEC §4 Phase 1
// acceptance item without perturbing control flow.
extern "C" {
volatile uint32_t native_sdcc_probe_bound = 0;      // compatible matched the sdhc1 nub
volatile uint32_t native_sdcc_started = 0;          // start() reached publication
volatile uint32_t native_sdcc_ready = 0;            // resume + EXT_CSD sane
volatile uint32_t native_sdcc_resume_error = 0;     // SdciCore error code on failure
volatile uint32_t native_sdcc_gpt_ok = 0;           // gptCheck() verdict
volatile uint32_t native_sdcc_read_requests = 0;
volatile uint32_t native_sdcc_read_failures = 0;
volatile uint64_t native_sdcc_capacity = 0;         // sectors from EXT_CSD[215..212]
volatile uint64_t native_sdcc_sectors_read = 0;
volatile uint32_t native_sdcc_store_attached = 0;   // transport attached to the store contract
unsigned char native_sdcc_first_sector_sha256[32] = {};
void native_sdcc_read_checkpoint(void *device) {
  __asm__ volatile("" : : "r"(device) : "memory");
}
}

namespace {
constexpr unsigned kTransferBytes = 65536;   // same staging budget as VirtioBlock
constexpr uint16_t kHandoffRca = 2;          // lk2nd's assigned RCA (probe-proven; SPEC Q1: adopt)
inline void writeBarrier() { __asm__ volatile("dsb oshst" ::: "memory"); }
}

// Kernel IO shim for SdciController: hc window is index 0, core window index 1
// (ADT reg order hc,core per SPEC §3.4 — do not reorder). Inhibited-cache
// mapping, writes posted behind dsb oshst exactly like NativeVirtioBlock.
class SdccPorts {
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
  void delay() { IODelay(10); }  // ~10 us, matching the probe's 192 cntpct ticks at 19.2 MHz

  // The device-proven preserve-restore across the HC_MODE boundary
  // (scripts/y35a/emmc_probe.cpp enableHostMode, run 2026-11-04: state 3,
  // 34/34 sectors). Enabling host mode resets power/SDCLK/DLL unless restored.
  // Deviation from the RAM probe, deliberate and SPEC-mandated (§2.1): the
  // probe's DLL_CONFIG_2 read/write at 0x1b4 lies OUTSIDE both DT windows
  // (hc ends 0x7824a1c); in a mapped kernel context it would abort. That
  // access was a same-value read-modify-write, so skipping it is equivalent.
  void enableHostMode() {
    uint8_t host = read8(0x28), power = read8(0x29);
    uint16_t clock = read16(0x2c), host2 = read16(0x3e);
    uint32_t dll = read32(0x100), vendor = read32(0x10c);
    coreWrite32(0x78, coreRead32(0x78) | 1);        // HC_MODE select
    write32(0x38, 0);                                // no interrupt signalling yet
    write16(0x2c, static_cast<uint16_t>(clock & ~4U));  // drop SDCLK across the boundary
    write32(0x10c, vendor);
    write8(0x28, host); write16(0x3e, host2);
    write32(0x100, dll);
    write8(0x29, power);
    // LK's power-event acknowledgement; regulators stay as the loader set them.
    uint32_t pending = coreRead32(0xdc);
    coreWrite32(0xe4, pending);
    uint32_t ack = coreRead32(0xe8);
    if (pending & 3) ack |= 1;
    if (pending & 12) ack |= 4;
    coreWrite32(0xe8, ack);
    for (unsigned i = 0; i < 50000 && !(read16(0x2c) & 2); ++i) delay();
    write16(0x2c, clock);  // restore the loader's full clock control last
  }
};

class NativeSdcc : public IOBlockStorageDevice {
  OSDeclareDefaultStructors(NativeSdcc)
  SdccPorts ports;
  // The transport core lives inline (repo kernel-C++ precedent avoids
  // placement new; the in-class initializer binds after `ports` is default-
  // constructed, declaration order). OSMetaClass::construct runs ctors.
  SdciController<SdccPorts> card{ports};
  IOMemoryMap *hcMapping = nullptr, *coreMapping = nullptr;
  IOLock *gate = nullptr;
  uint8_t *extCsd = nullptr, *staging = nullptr;
  uint64_t capacity = 0;
  bool online = false;
  sdcc::SdccStore<SdciController<SdccPorts>> store;  // Phase 2 contract surface
  IOReturn readSectors(uint64_t sector, uint32_t bytes);
 public:
  IOService *probe(IOService *provider, SInt32 *score) override;
  bool start(IOService *provider) override;
  void stop(IOService *provider) override;
  void free() override;
  IOReturn doEjectMedia() override { return kIOReturnUnsupported; }
  IOReturn doFormatMedia(UInt64) override { return kIOReturnNotWritable; }
  UInt32 doGetFormatCapacities(UInt64 *, UInt32) const override { return 0; }
  char *getVendorString() override { return const_cast<char *>("Qualcomm"); }
  char *getProductString() override { return const_cast<char *>("Y35A eMMC sdhc1"); }
  char *getRevisionString() override { return const_cast<char *>("sdci-1-resume"); }
  char *getAdditionalDeviceInfoString() override { return const_cast<char *>("MSM8916 SDHCI PIO, lk2nd handoff"); }
  IOReturn reportBlockSize(UInt64 *value) override { *value = 512; return kIOReturnSuccess; }
  IOReturn reportEjectability(bool *value) override { *value = false; return kIOReturnSuccess; }
  IOReturn reportMaxValidBlock(UInt64 *value) override { *value = capacity - 1; return kIOReturnSuccess; }
  IOReturn reportMediaState(bool *present, bool *changed) override {
    *present = online; if (changed) *changed = false; return kIOReturnSuccess;
  }
  IOReturn reportRemovability(bool *value) override { *value = false; return kIOReturnSuccess; }
  IOReturn reportWriteProtection(bool *value) override { *value = true; return kIOReturnSuccess; }
  IOReturn doSynchronizeCache() override { return online ? kIOReturnSuccess : kIOReturnNotReady; }
  IOReturn doSynchronize(UInt64, UInt64, IOOptionBits) override { return doSynchronizeCache(); }
  IOReturn getWriteCacheState(bool *value) override { *value = false; return kIOReturnSuccess; }
  IOReturn setWriteCacheState(bool) override { return kIOReturnUnsupported; }
  IOReturn doAsyncReadWrite(IOMemoryDescriptor *, UInt64, UInt64, IOStorageAttributes *, IOStorageCompletion *) override;
  // Store-contract accessors (RamBlock PersistOverlay through the C shims at
  // the bottom of this file). Units are persist::kBlock (4096 B). Every call
  // serializes on the same gate as media I/O.
  unsigned storeMode();
  int storeOpen(uint64_t blocks, uint64_t *first, const char **why);
  bool storeRead(uint64_t block, uint32_t count, void *dst);
  bool storeWrite(uint64_t block, uint32_t count, const void *src);
  bool storeSync();
  unsigned storeGptCheck();
};
OSDefineMetaClassAndStructors(NativeSdcc, IOBlockStorageDevice)

// One sdhc1 per supported board; the store C shims resolve through it.
static NativeSdcc *gSdccInstance = nullptr;

IOService *NativeSdcc::probe(IOService *provider, SInt32 *score)
{
  // The ADT writes compatible = "qcom,sdhci-msm\0" (15 bytes) for the sdhc1
  // nub, matching the stock DTB string. Same shape as NativeVirtioBlock::probe.
  OSData *compatible = OSDynamicCast(OSData, provider->getProperty("compatible"));
  if (!compatible || compatible->getLength() != 15 ||
      memcmp(compatible->getBytesNoCopy(), "qcom,sdhci-msm", 15)) return nullptr;
  native_sdcc_probe_bound = 1;
  return IOBlockStorageDevice::probe(provider, score);
}

bool NativeSdcc::start(IOService *provider)
{
  if (!IOBlockStorageDevice::start(provider)) return false;
  gSdccInstance = this;  // single-instance board (one sdhc1); reset in free()
  if (provider->getResources() != kIOReturnSuccess) return false;
  hcMapping = provider->mapDeviceMemoryWithIndex(0, kIOMapAnywhere | kIOMapInhibitCache);
  coreMapping = provider->mapDeviceMemoryWithIndex(1, kIOMapAnywhere | kIOMapInhibitCache);
  if (!hcMapping || hcMapping->getLength() < 0x11c || !coreMapping || coreMapping->getLength() < 0x800)
    return false;
  ports.hc = static_cast<uintptr_t>(hcMapping->getVirtualAddress());
  ports.core = static_cast<uintptr_t>(coreMapping->getVirtualAddress());
  gate = IOLockAlloc();
  extCsd = static_cast<uint8_t *>(IOMalloc(512));
  staging = static_cast<uint8_t *>(IOMalloc(kTransferBytes));
  if (!gate || !extCsd || !staging) return false;

  // Phase 1 acceptance sequence (SPEC §4): resume the handed-over card,
  // confirm the user-area capacity, verify GPT against the byte-verified
  // table (emmc-gpt-verified-20261104.json), hash sector 0 for comparison.
  if (!card.resume(kHandoffRca, extCsd)) {
    native_sdcc_resume_error = card.error;
    return false;
  }
  capacity = card.sectors();
  native_sdcc_capacity = capacity;
  native_sdcc_gpt_ok = card.gptCheck() ? 1 : 2;  // gptCheck clears ready on I/O loss
  native_sdcc_resume_error = card.error;
  if (!capacity || card.error == 9) return false;
  // Phase 2 surface: the store contract exists from here, but stays mode 0
  // (volatile disk) until the owner approves the window — writes refuse
  // before touching the bus either way.
  store.attach(&card);
  native_sdcc_store_attached = 1;
  // The transport is live from here; readSectors is gated on this flag.
  online = true;
  IOLockLock(gate);
  IOReturn first = readSectors(0, 512);
  IOLockUnlock(gate);
  if (first) { online = false; return false; }
  SHA256_CTX hash;
  SHA256_Init(&hash);
  SHA256_Update(&hash, staging, 512);
  SHA256_Final(native_sdcc_first_sector_sha256, &hash);
  native_sdcc_ready = 1;
  native_sdcc_started = 1;
  native_sdcc_read_checkpoint(this);
  registerService();
  return true;
}

IOReturn NativeSdcc::readSectors(uint64_t sector, uint32_t bytes)
{
  if (!online || !bytes || (bytes & 511) || bytes > kTransferBytes ||
      sector >= capacity || bytes / 512 > capacity - sector) return kIOReturnBadArgument;
  if (!card.readSectors(static_cast<uint32_t>(sector), bytes / 512, staging)) {
    __atomic_fetch_add(&native_sdcc_read_failures, 1, __ATOMIC_RELAXED);
    return kIOReturnIOError;
  }
  __atomic_fetch_add(&native_sdcc_read_requests, 1, __ATOMIC_RELAXED);
  __atomic_fetch_add(&native_sdcc_sectors_read, bytes / 512, __ATOMIC_RELAXED);
  return kIOReturnSuccess;
}

IOReturn NativeSdcc::doAsyncReadWrite(IOMemoryDescriptor *buffer, UInt64 block, UInt64 count,
                                      IOStorageAttributes *, IOStorageCompletion *completion)
{
  if (!buffer || !completion || !completion->action || !count || block >= capacity ||
      count > capacity - block || count > UINT64_MAX / 512 || buffer->getLength() < count * 512)
    return kIOReturnBadArgument;
  if (buffer->getDirection() != kIODirectionIn) return kIOReturnNotWritable;  // Phase 1: read-only
  uint64_t actual = 0;
  IOReturn result = kIOReturnNotReady;
  IOLockLock(gate);
  while (online && actual < count * 512) {
    uint32_t bytes = static_cast<uint32_t>(count * 512 - actual > kTransferBytes
                                               ? kTransferBytes : count * 512 - actual);
    result = readSectors(block + actual / 512, bytes);
    if (result) break;
    if (buffer->writeBytes(actual, staging, bytes) != bytes) { result = kIOReturnIOError; break; }
    actual += bytes;
  }
  IOLockUnlock(gate);
  completion->action(completion->target, completion->parameter, result, actual);
  return kIOReturnSuccess;
}

void NativeSdcc::stop(IOService *provider)
{
  // Phase 1 PIO completes every transfer synchronously under the gate, so no
  // device operation can outlive the driver; quiescing is just closing state.
  online = false;
  native_sdcc_ready = 0;
  IOBlockStorageDevice::stop(provider);
}

void NativeSdcc::free()
{
  store.detach();
  if (gSdccInstance == this) gSdccInstance = nullptr;
  if (staging) { IOFree(staging, kTransferBytes); staging = nullptr; }
  if (extCsd) { IOFree(extCsd, 512); extCsd = nullptr; }
  if (gate) { IOLockFree(gate); gate = nullptr; }
  if (hcMapping) { hcMapping->release(); hcMapping = nullptr; }
  if (coreMapping) { coreMapping->release(); coreMapping = nullptr; }
  IOBlockStorageDevice::free();
}

unsigned NativeSdcc::storeMode() {
  if (!gate) return 0u;
  IOLockLock(gate);
  unsigned result = store.mode();
  IOLockUnlock(gate);
  return result;
}
int NativeSdcc::storeOpen(uint64_t blocks, uint64_t *first, const char **why) {
  if (!gate || !first || !why) return 0;
  IOLockLock(gate);
  bool ok = store.open(blocks, first, why);
  IOLockUnlock(gate);
  return ok ? 1 : 0;
}
bool NativeSdcc::storeRead(uint64_t block, uint32_t count, void *dst) {
  if (!gate) return false;
  IOLockLock(gate);
  bool ok = store.read(block, count, dst);
  IOLockUnlock(gate);
  return ok;
}
bool NativeSdcc::storeWrite(uint64_t block, uint32_t count, const void *src) {
  if (!gate) return false;
  IOLockLock(gate);
  bool ok = store.write(block, count, src);
  IOLockUnlock(gate);
  return ok;
}
bool NativeSdcc::storeSync() {
  if (!gate) return false;
  IOLockLock(gate);
  bool ok = store.sync();
  IOLockUnlock(gate);
  return ok;
}
unsigned NativeSdcc::storeGptCheck() {
  if (!gate) return 0xff;
  IOLockLock(gate);
  unsigned result = store.gptCheck();
  IOLockUnlock(gate);
  return result;
}

// The six weak-imported symbols RamBlock's PersistOverlay resolves at link
// time (drivers/RamBlock/NativeRamBlock.cpp). Same C contract, sdhc1
// transport. gpt_check's zero-is-intact convention is RamBlock's (SPEC 3.7).
extern "C" {
unsigned native_ufs_store_mode(void) {
  NativeSdcc *d = gSdccInstance;
  return d ? d->storeMode() : 0;
}
int native_ufs_store_open(uint64_t blocks, uint64_t *first, const char **why) {
  NativeSdcc *d = gSdccInstance;
  return d ? d->storeOpen(blocks, first, why) : 0;
}
int native_ufs_store_read(uint64_t block, uint32_t count, void *dst) {
  NativeSdcc *d = gSdccInstance;
  return d && d->storeRead(block, count, dst) ? 1 : 0;
}
int native_ufs_store_write(uint64_t block, uint32_t count, const void *src) {
  NativeSdcc *d = gSdccInstance;
  return d && d->storeWrite(block, count, src) ? 1 : 0;
}
int native_ufs_store_sync(void) {
  NativeSdcc *d = gSdccInstance;
  return d && d->storeSync() ? 1 : 0;
}
unsigned native_ufs_store_gpt_check(void) {
  NativeSdcc *d = gSdccInstance;
  return d ? d->storeGptCheck() : 0xff;
}
}
