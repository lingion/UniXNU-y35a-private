// SPDX-License-Identifier: BSD-2-Clause-Patent
// NativeQupI2c — kernel shell for the QUP SE I2C engine (see NativeQupI2c.h).
// The transport code is I2cCore.h's QupI2c<QupPorts>, the identical template
// the T1 host suite exercises over the fake SE (Test/i2c_host.cpp) and that
// touch_host case 17 runs under DigitizerBoot. The MMIO window discipline is
// NativeSdcc's: mapDeviceMemoryWithIndex with kIOMapAnywhere|kIOMapInhibitCache
// and a dsb oshst after every posted write.
//
// One qup_i2c5 per board: the engine state lives in the driver's members
// (ports/core/seMapping/gate/slaveAddr, declaration order binding core to
// ports like NativeSdcc's card{ports}). Resources owned per-instance mean
// free() releases exactly this instance's, no global bookkeeping.
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOLocks.h>
#include <IOKit/IORegistryEntry.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSNumber.h>

#include "I2cCore.h"
#include "NativeQupI2c.h"

// Boot-time checkpoints (extern "C" volatiles, NativeSdcc discipline: each
// records one acceptance item without perturbing control flow; read back via
// the proven fastboot staging / GDB observer path).
extern "C" {
volatile uint32_t native_qup_i2c_attached = 0;   // compatible matched the qup_i2c5 nub
volatile uint32_t native_qup_i2c_started = 0;    // start() reached registration
volatile uint32_t native_qup_i2c_dt_child = 0;   // rmi4 grandchild resolved
volatile uint32_t native_qup_i2c_error = 0;      // qup::Err or DtFail code below
volatile uint32_t native_qup_i2c_transfers = 0;  // successful bus transactions
volatile uint32_t native_qup_i2c_failures = 0;   // failed bus transactions
}

namespace {
constexpr unsigned kSeWindowBytes = 0x600;  // ADT reg[0] length (dtb10 parity)
// clk-freq-in from the stock DTB (19.2 MHz board clock); the 400 kHz output
// is the DT clock-frequency value the T1 divider contract consumes.
constexpr uint32_t kClockSrcHz = 19200000;
constexpr uint32_t kClockBusHz = 400000;

// DT-walk failure codes, extending the qup::Err space in native_qup_i2c_error.
enum : unsigned {
  DtFailMapping = 0x100,  // SE window missing or short
  DtFailRmiNode = 0x101,  // rmi4 child node missing on the DT plane
  DtFailFacts = 0x102,    // reg/dims present but not usable, or publish failed
};

// DT cell readers. The ADT emitter writes every cell little-endian
// (make_adt.py struct '<I'/'<Q' throughout) and the other in-tree consumers
// (ArmDTPlatform::hasNVRAMProxy; NativeSdcc resolving sdhc1 through the same
// ADT) read LE, so the shell does the same.
bool cellU32(OSObject *value, unsigned &out) {
  if (OSData *data = OSDynamicCast(OSData, value)) {
    if (data->getLength() != 4) return false;
    const uint8_t *b = static_cast<const uint8_t *>(data->getBytesNoCopy());
    out = unsigned(b[0]) | (unsigned(b[1]) << 8) | (unsigned(b[2]) << 16) |
          (unsigned(b[3]) << 24);
    return true;
  }
  if (OSNumber *num = OSDynamicCast(OSNumber, value)) {
    if (num->numberOfBits() > 32) return false;
    out = static_cast<unsigned>(num->unsigned32BitValue());
    return true;
  }
  return false;
}
}  // namespace

void QupPorts::delay() { IODelay(10); }  // header declares it out of line

const char *const NativeQupI2c::kRmiAddressKey = "rmi-address";
const char *const NativeQupI2c::kRmiCompatibleKey = "rmi-compatible";
const char *const NativeQupI2c::kAttnPolarityKey = "attn-polarity";
const char *const NativeQupI2c::kResetGpioKey = "reset-gpio";
const char *const NativeQupI2c::kIrqGpioKey = "irq-gpio";
const char *const NativeQupI2c::kTsDimensionKey = "ts-dimension";
const char *const NativeQupI2c::kLcdDimensionKey = "lcd-dimension";

OSDefineMetaClassAndStructors(NativeQupI2c, IOService)

// republish the rmi4 grandchild's facts as properties on the driver itself
// (member so setProperty targets `this`; the digitizer reads these keys from
// its provider once the personality engine attaches it).
bool NativeQupI2c::publishRmiFacts(IORegistryEntry *rmi) {
  // reg: one #address-cells=1 child unit address — the 7-bit slave.
  unsigned addr = 0;
  if (!cellU32(rmi->getProperty("reg"), addr) || addr > 0x7f) return false;
  slaveAddr = uint8_t(addr);

  bool ok = setProperty(kRmiAddressKey, static_cast<unsigned long long>(addr), 32);

  if (OSData *comp = OSDynamicCast(OSData, rmi->getProperty("compatible")))
    ok = setProperty(kRmiCompatibleKey, const_cast<void *>(comp->getBytesNoCopy()),
                     comp->getLength()) && ok;
  else
    ok = false;

  unsigned v = 0;
  ok = cellU32(rmi->getProperty("attn_polarity"), v) &&
       setProperty(kAttnPolarityKey, static_cast<unsigned long long>(v), 32) && ok;
  ok = cellU32(rmi->getProperty("reset-gpio"), v) &&
       setProperty(kResetGpioKey, static_cast<unsigned long long>(v), 32) && ok;
  ok = cellU32(rmi->getProperty("irq-gpio"), v) &&
       setProperty(kIrqGpioKey, static_cast<unsigned long long>(v), 32) && ok;

  // Panel geometry publishes verbatim as the ADT's 8-byte cells (two u32 LE),
  // the same bytes RmiCore's TS_DIM/LCD_DIM defaults were locked against.
  OSData *ts = OSDynamicCast(OSData, rmi->getProperty("ts-dimension"));
  OSData *lcd = OSDynamicCast(OSData, rmi->getProperty("lcd-dimension"));
  if (ts && ts->getLength() == 8)
    ok = setProperty(kTsDimensionKey, const_cast<void *>(ts->getBytesNoCopy()), 8) && ok;
  else
    ok = false;
  if (lcd && lcd->getLength() == 8)
    ok = setProperty(kLcdDimensionKey, const_cast<void *>(lcd->getBytesNoCopy()), 8) && ok;
  else
    ok = false;
  return ok;
}

IOService *NativeQupI2c::probe(IOService *provider, SInt32 *score) {
  // The ADT writes compatible = "qcom,i2c-msm-v2\0" (17 bytes) for the
  // qup_i2c5 nub; the length + memcmp idiom is NativeSdcc::probe's (15 for
  // "qcom,sdhci-msm").
  OSData *compatible = OSDynamicCast(OSData, provider->getProperty("compatible"));
  if (!compatible || compatible->getLength() != 17 ||
      memcmp(compatible->getBytesNoCopy(), "qcom,i2c-msm-v2", 17))
    return nullptr;
  native_qup_i2c_attached = 1;
  return IOService::probe(provider, score);
}

bool NativeQupI2c::start(IOService *provider) {
  if (!IOService::start(provider)) return false;
  gate = IOLockAlloc();
  if (!gate) return false;

  if (provider->getResources() != kIOReturnSuccess) return false;
  // reg index 0 is the SE window (reg-names "qup_mem\0bam_mem\0" — the ADT
  // order NativeSdcc depends on for sdhc1, same convention here). T1/T3 run
  // SE PIO only; the BAM window is deliberately NOT mapped (plan
  // Architecture Decision 1: no DMA for touch frames).
  seMapping =
      provider->mapDeviceMemoryWithIndex(0, kIOMapAnywhere | kIOMapInhibitCache);
  if (!seMapping || seMapping->getLength() < kSeWindowBytes) {
    native_qup_i2c_error = DtFailMapping;
    return false;
  }
  ports.se = static_cast<uintptr_t>(seMapping->getVirtualAddress());
  core.setClock(kClockSrcHz, kClockBusHz);

  // Attach assert (skeleton decision): the engine must be idle when the
  // session opens — lk2nd hands the bus over between transactions. If the
  // status word reports an active line or carries error bits, one SW_RESET
  // teardown (QupI2c::reset, the T1.4 API) retries; a still-busy engine
  // refuses start() rather than driving into it.
  IOLockLock(gate);
  bool idle = (ports.read32(qup::SE_I2C_STATUS) &
               (qup::BUS_ACTIVE | qup::STATUS_ERROR_MASK)) == 0;
  if (!idle && core.reset())
    idle = (ports.read32(qup::SE_I2C_STATUS) &
            (qup::BUS_ACTIVE | qup::STATUS_ERROR_MASK)) == 0;
  IOLockUnlock(gate);
  if (!idle) {
    native_qup_i2c_error = core.lastError();
    return false;
  }

  // DT grandchild resolution: the IOPlatformDevice nub is registered in
  // gIODTPlane at its real DT position (IODTPlatformExpert::createNub ->
  // IOPlatformDevice::init(from, gIODTPlane)), so childFromPath("rmi4") on
  // the provider walks the ADT's nested slave node (rmi4 under qup_i2c5).
  IORegistryEntry *rmi = provider->childFromPath("rmi4", gIODTPlane);
  if (!rmi) {
    native_qup_i2c_error = DtFailRmiNode;
    return false;
  }
  native_qup_i2c_dt_child = 1;
  bool published = publishRmiFacts(rmi);
  rmi->release();  // childFromPath returns a retained entry
  if (!published) {
    native_qup_i2c_error = DtFailFacts;
    return false;
  }

  native_qup_i2c_started = 1;
  registerService();  // the personality engine can now attach NativeHidDigitizer
  return true;
}

bool NativeQupI2c::write(const uint8_t *b, unsigned len) {
  if (!gate || !b || !len) return false;
  qup::Msg m{slaveAddr, false, uint16_t(len), const_cast<uint8_t *>(b)};
  IOLockLock(gate);
  bool ok = core.xfer(&m, 1);
  IOLockUnlock(gate);
  if (ok) __atomic_fetch_add(&native_qup_i2c_transfers, 1, __ATOMIC_RELAXED);
  else __atomic_fetch_add(&native_qup_i2c_failures, 1, __ATOMIC_RELAXED);
  return ok;
}

bool NativeQupI2c::readAt(uint8_t reg, uint8_t *buf, unsigned len) {
  if (!gate || !buf || !len || len > 256) return false;
  qup::Msg list[2] = {{slaveAddr, false, 1, &reg},
                      {slaveAddr, true, uint16_t(len), buf}};
  IOLockLock(gate);
  bool ok = core.xfer(list, 2);  // I2cCore joins into one repeated-start txn
  IOLockUnlock(gate);
  if (ok) __atomic_fetch_add(&native_qup_i2c_transfers, 1, __ATOMIC_RELAXED);
  else __atomic_fetch_add(&native_qup_i2c_failures, 1, __ATOMIC_RELAXED);
  return ok;
}

bool NativeQupI2c::resetBus() {
  if (!gate) return false;
  IOLockLock(gate);
  bool ok = core.reset();
  IOLockUnlock(gate);
  return ok;
}

unsigned NativeQupI2c::lastError() const { return core.lastError(); }

void NativeQupI2c::stop(IOService *provider) {
  // Every transfer completes synchronously under the gate (polled PIO), so no
  // engine operation outlives the driver; quiescing is closing state.
  native_qup_i2c_started = 0;
  IOService::stop(provider);
}

void NativeQupI2c::free() {
  if (seMapping) { seMapping->release(); seMapping = nullptr; }
  if (gate) { IOLockFree(gate); gate = nullptr; }
  ports.se = 0;
  IOService::free();
}
