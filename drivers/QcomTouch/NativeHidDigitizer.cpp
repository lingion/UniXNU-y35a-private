// SPDX-License-Identifier: BSD-2-Clause-Patent
// NativeHidDigitizer — see NativeHidDigitizer.h. Kernel shell over the
// certified IOHIDFamily 1090.270.6 shim; the bring-up code path is
// literally DigitizerBoot.h (locked by touch_host case 17) and the decode
// path is literally RmiCore.h (locked by touch_host cases 1-16).
//
// Attach note (locked design decision): the T4.2 personality publishes this
// class under IOProviderClass=NativeQupI2c, so the matching engine hands the
// bus to start()/handleStart as `provider` — the same nub-attach pattern
// NativeSdcc uses on sdhc1. The user-space IOServiceGetMatchingService does
// not exist in the 4903 kernel headers (it is IOKitLib, user side); its
// kernel-side analogue IOService::copyMatchingService is not needed because
// the provider already IS the bus service.
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSNumber.h>

#include "../QcomQupI2c/NativeQupI2c.h"
#include "NativeHidDigitizer.h"
#include "RmiCore.h"

extern "C" {
volatile uint32_t native_hid_digitizer_started = 0;  // base start() completed
volatile uint32_t native_hid_boot_stage = 0;   // highest bringUp stage (1..5)
volatile uint32_t native_hid_identity_ok = 0;  // bringUp returned true
volatile uint32_t native_hid_error = 0;        // bringUp refusal code, or
                                               // 0x1000|qup::Err on transport
volatile uint32_t native_hid_frames = 0;       // pollFrame successes
volatile uint32_t native_hid_frame_failures = 0;  // pollFrame failures
}

namespace {
// Kernel-side stage logger: records progress into the boot-stage checkpoint;
// refusals land in native_hid_error at the caller (bringUp's return).
struct KernelSeqLog {
  void stage(unsigned s) {
    if (s > native_hid_boot_stage) native_hid_boot_stage = s;
  }
  void refusal(unsigned r) { native_hid_error = r; }
};

// MT1-style digitizer input report (byte 0 Contact Count, then five 7-byte
// Finger collections {TransducerIndex 8, X 16 (0..719), Y 16 (0..1279),
// TipPressure 8, TipSwitch+Confidence 2 bits, 6-bit pad} = 56 bits/slot).
// The blob layout DigitizerBoot.h encodeBlob produces matches it bit for
// bit; logical maxima come from the DT lcd dimensions (ADT 720x1280).
constexpr uint8_t kReportDescriptor[] = {
    0x05, 0x0D, 0x09, 0x04, 0xA1, 0x01, 0x15, 0x00, 0x25, 0x05, 0x75, 0x08,
    0x95, 0x01, 0x09, 0x54, 0x81, 0x02, 0x09, 0x55, 0xB1, 0x02, 0x95, 0x01,
    0x09, 0x22, 0xA1, 0x02, 0x25, 0xFF, 0x75, 0x08, 0x95, 0x01, 0x09, 0x38,
    0x81, 0x02, 0x05, 0x01, 0x09, 0x30, 0x26, 0xAF, 0x02, 0x75, 0x10, 0x95,
    0x01, 0x81, 0x02, 0x09, 0x31, 0x26, 0xFF, 0x04, 0x81, 0x02, 0x05, 0x0D,
    0x09, 0x30, 0x25, 0xFF, 0x75, 0x08, 0x81, 0x02, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x02, 0x09, 0x42, 0x09, 0x47, 0x81, 0x02, 0x75, 0x06,
    0x95, 0x01, 0x81, 0x03, 0xC0, 0x09, 0x22, 0xA1, 0x02, 0x25, 0xFF, 0x75,
    0x08, 0x95, 0x01, 0x09, 0x38, 0x81, 0x02, 0x05, 0x01, 0x09, 0x30, 0x26,
    0xAF, 0x02, 0x75, 0x10, 0x95, 0x01, 0x81, 0x02, 0x09, 0x31, 0x26, 0xFF,
    0x04, 0x81, 0x02, 0x05, 0x0D, 0x09, 0x30, 0x25, 0xFF, 0x75, 0x08, 0x81,
    0x02, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x02, 0x09, 0x42, 0x09,
    0x47, 0x81, 0x02, 0x75, 0x06, 0x95, 0x01, 0x81, 0x03, 0xC0, 0x09, 0x22,
    0xA1, 0x02, 0x25, 0xFF, 0x75, 0x08, 0x95, 0x01, 0x09, 0x38, 0x81, 0x02,
    0x05, 0x01, 0x09, 0x30, 0x26, 0xAF, 0x02, 0x75, 0x10, 0x95, 0x01, 0x81,
    0x02, 0x09, 0x31, 0x26, 0xFF, 0x04, 0x81, 0x02, 0x05, 0x0D, 0x09, 0x30,
    0x25, 0xFF, 0x75, 0x08, 0x81, 0x02, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01,
    0x95, 0x02, 0x09, 0x42, 0x09, 0x47, 0x81, 0x02, 0x75, 0x06, 0x95, 0x01,
    0x81, 0x03, 0xC0, 0x09, 0x22, 0xA1, 0x02, 0x25, 0xFF, 0x75, 0x08, 0x95,
    0x01, 0x09, 0x38, 0x81, 0x02, 0x05, 0x01, 0x09, 0x30, 0x26, 0xAF, 0x02,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x02, 0x09, 0x31, 0x26, 0xFF, 0x04, 0x81,
    0x02, 0x05, 0x0D, 0x09, 0x30, 0x25, 0xFF, 0x75, 0x08, 0x81, 0x02, 0x15,
    0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x02, 0x09, 0x42, 0x09, 0x47, 0x81,
    0x02, 0x75, 0x06, 0x95, 0x01, 0x81, 0x03, 0xC0, 0x09, 0x22, 0xA1, 0x02,
    0x25, 0xFF, 0x75, 0x08, 0x95, 0x01, 0x09, 0x38, 0x81, 0x02, 0x05, 0x01,
    0x09, 0x30, 0x26, 0xAF, 0x02, 0x75, 0x10, 0x95, 0x01, 0x81, 0x02, 0x09,
    0x31, 0x26, 0xFF, 0x04, 0x81, 0x02, 0x05, 0x0D, 0x09, 0x30, 0x25, 0xFF,
    0x75, 0x08, 0x81, 0x02, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x02,
    0x09, 0x42, 0x09, 0x47, 0x81, 0x02, 0x75, 0x06, 0x95, 0x01, 0x81, 0x03,
    0xC0, 0xC0,
};

bool leU32(const uint8_t *b, unsigned &out) {
  out = unsigned(b[0]) | (unsigned(b[1]) << 8) | (unsigned(b[2]) << 16) |
        (unsigned(b[3]) << 24);
  return true;
}
}  // namespace

OSDefineMetaClassAndStructors(NativeHidDigitizer, IOHIDDevice)

IOService *NativeHidDigitizer::probe(IOService *provider, SInt32 *score) {
  // The personality engine already filtered IOProviderClass=NativeQupI2c;
  // refuse anything that is not the bus shell, and require the IC identity
  // fact the bus published (rmi-compatible, ADT T4.1 "synaptics_3202\0").
  if (!OSDynamicCast(NativeQupI2c, provider)) return nullptr;
  OSData *comp = OSDynamicCast(
      OSData, provider->getProperty(NativeQupI2c::kRmiCompatibleKey));
  if (!comp) return nullptr;
  return IOService::probe(provider, score);
}

bool NativeHidDigitizer::handleStart(IOService *provider) {
  if (!IOHIDDevice::handleStart(provider)) return false;
  bus = OSDynamicCast(NativeQupI2c, provider);
  if (!bus) return false;

  // ---- config from the bus-published facts. Defaults stay compiled-in (the
  // RmiCore TS_DIM/LCD_DIM contract values); DT cells override them. ----
  if (OSNumber *addr = OSDynamicCast(
          OSNumber, provider->getProperty(NativeQupI2c::kRmiAddressKey)))
    cfg.slave_addr = static_cast<uint32_t>(addr->unsigned32BitValue());
  if (OSData *dims = OSDynamicCast(
          OSData, provider->getProperty(NativeQupI2c::kTsDimensionKey));
      dims && dims->getLength() == 8) {
    const uint8_t *b = static_cast<const uint8_t *>(dims->getBytesNoCopy());
    leU32(b, cfg.ts.w);
    leU32(b + 4, cfg.ts.h);
  }
  if (OSData *dims = OSDynamicCast(
          OSData, provider->getProperty(NativeQupI2c::kLcdDimensionKey));
      dims && dims->getLength() == 8) {
    const uint8_t *b = static_cast<const uint8_t *>(dims->getBytesNoCopy());
    leU32(b, cfg.lcd.w);
    leU32(b + 4, cfg.lcd.h);
  }

  gate = IOLockAlloc();
  pkt = static_cast<uint8_t *>(IOMalloc(256));  // bringUp caps the window at 256
  if (!gate || !pkt) return false;

  // ---- the real sequence over the real transport: identical template code
  // the host suite locks in case 17. A refusal fails handleStart, which
  // fails start() — the bus stays reset for a later session (plan T2.2
  // refuse-boot discipline). ----
  rmi::RmiXport<NativeQupI2c> xport(*bus);
  KernelSeqLog log;
  if (!digitizerboot::bringUp(xport, cfg, boot, log)) {
    if (native_hid_error != digitizerboot::RefuseTransport) {
      native_hid_error = 0x1000u | native_hid_error;  // keep refusal distinguishable
    } else {
      native_hid_error = 0x1000u | bus->lastError();
    }
    bus->resetBus();  // T1.4 teardown so the next session starts clean
    return false;
  }
  native_hid_identity_ok = 1;

  // The slave address the bus will actually drive must equal what the
  // digitizer's transport assumed — they came from the same DT cell.
  setProperty("native-hid-window-size",
              static_cast<unsigned long long>(boot.window), 8);
  setProperty("native-hid-fingers",
              static_cast<unsigned long long>(boot.f11.fingers()), 8);
  online = true;
  return true;
}

bool NativeHidDigitizer::start(IOService *provider) {
  if (!IOHIDDevice::start(provider)) return false;
  // IOHIDDevice::start ran handleStart (bring-up), fetched the report
  // descriptor, published HID properties and registered the service
  // (shim IOHIDDevice.h start contract). From here the polled path is live.
  native_hid_digitizer_started = 1;
  return true;
}

IOReturn NativeHidDigitizer::newReportDescriptor(
    IOMemoryDescriptor **descriptor) const {
  if (!descriptor) return kIOReturnBadArgument;
  IOBufferMemoryDescriptor *buf = IOBufferMemoryDescriptor::withBytes(
      kReportDescriptor, sizeof kReportDescriptor, kIODirectionNone);
  if (!buf) {
    *descriptor = nullptr;
    return kIOReturnNoMemory;
  }
  *descriptor = buf;  // withBytes returns a retained object (OSPtr == raw ptr
                      // in the non-shared-ptr dialect the shim compiles under)
  return kIOReturnSuccess;
}

bool NativeHidDigitizer::pollFrame() {
  if (!online || !bus) return false;
  const rmi::FnDesc &f11 = boot.fns[boot.i11];
  // Fresh paging transport per call: the page cache is an optimization, and
  // every readBlock re-anchors via its address byte (RmiCore.h transport
  // notes), so a cold cache only ever costs one redundant {0xff,page}.
  rmi::RmiXport<NativeQupI2c> xport(*bus);
  // v4.9 attention read: the full pkt_size window at F11 data base
  // (rmi_f11_attention:1244-1248; rmi_i2c never sets attn_data).
  if (!xport.readBlock(f11.data, pkt, boot.window)) {
    __atomic_fetch_add(&native_hid_frame_failures, 1, __ATOMIC_RELAXED);
    return false;
  }
  rmi::TouchFrame fr;
  if (rmi::decodeF11(pkt, boot.f11, fr) != rmi::F_OK) {
    __atomic_fetch_add(&native_hid_frame_failures, 1, __ATOMIC_RELAXED);
    return false;
  }
  uint8_t blob[kReportBytes];
  digitizerboot::encodeBlob(fr, cfg, blob);
  IOLockLock(gate);
  memcpy(report, blob, kReportBytes);  // snapshot publication under one lock
  IOLockUnlock(gate);
  __atomic_fetch_add(&native_hid_frames, 1, __ATOMIC_RELAXED);
  return true;
}

unsigned NativeHidDigitizer::snapshot(uint8_t *out, unsigned outLen) const {
  if (!out || !gate) return 0;
  unsigned n = outLen < kReportBytes ? outLen : kReportBytes;
  IOLockLock(gate);
  memcpy(out, report, n);
  IOLockUnlock(gate);
  return n;
}

void NativeHidDigitizer::stop(IOService *provider) {
  online = false;
  native_hid_digitizer_started = 0;
  IOHIDDevice::stop(provider);
}

void NativeHidDigitizer::free() {
  if (gate) { IOLockFree(gate); gate = nullptr; }
  if (pkt) { IOFree(pkt, 256); pkt = nullptr; }
  bus = nullptr;  // the provider reference belongs to the attach, not us
  IOHIDDevice::free();
}
