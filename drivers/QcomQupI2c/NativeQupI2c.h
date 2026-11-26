// SPDX-License-Identifier: BSD-2-Clause-Patent
// NativeQupI2c — IOService shell for the MSM8916 BLSP1 QUP5 I2C SE engine
// (ADT node /arm-io/qup_i2c5, compatible "qcom,i2c-msm-v2"), vivo Y35A touch
// bus. Attaches on the platform-device nub like NativeSdcc on sdhc1, maps the
// SE window (reg index 0, 0x600 bytes), runs the transport-identical
// QupI2c<QupPorts> core from I2cCore.h, resolves the rmi4 grandchild on the
// device-tree plane and republishes its facts (reg/attn_polarity/GPIOs/
// dimensions) as properties on itself, then registerService() so the T4.2
// personality (IOProviderClass=NativeQupI2c) attaches NativeHidDigitizer.
//
// Kernel-only header: it includes I2cCore.h (pure C++ template, host suites
// keep using it directly) and the IOService chain. The engine core is an
// inline member bound by declaration order exactly like NativeSdcc's
// `card{ports}` — OSMetaClass::construct runs the ctor, no placement new.
#ifndef QCOMQUPI2C_NATIVEQUPI2C_H
#define QCOMQUPI2C_NATIVEQUPI2C_H

#include <IOKit/IOService.h>

#include "I2cCore.h"

class IOMemoryMap;
// IOLocks.h defines IOLock exactly this way; re-declaring the typedef keeps
// the header free of IOLib while the member is only ever a pointer.
typedef struct _IOLock IOLock;

// Kernel IO shim for QupI2c<IO> — the SdccPorts idiom: one mapped SE window,
// volatile 32-bit accessors at window-relative offsets, dsb oshst after each
// posted write, ~10 us delay matching the host model's spin accounting.
class QupPorts {
 public:
  uintptr_t se = 0;
  uint32_t read32(unsigned r) const {
    return *reinterpret_cast<volatile uint32_t *>(se + r);
  }
  void write32(unsigned r, uint32_t v) {
    *reinterpret_cast<volatile uint32_t *>(se + r) = v;
    __asm__ volatile("dsb oshst" ::: "memory");
  }
  void delay();  // IODelay(10) — defined in the .cpp to keep IOLib out here
};

class NativeQupI2c : public IOService {
  OSDeclareDefaultStructors(NativeQupI2c)

 public:
  // Property keys the bus driver publishes for the digitizer (values are
  // read verbatim from the DT rmi4 grandchild; see T4.1 ADT node).
  static const char *const kRmiAddressKey;      // OSNumber (0x20, from reg)
  static const char *const kRmiCompatibleKey;   // OSData "synaptics_3202\0"
  static const char *const kAttnPolarityKey;    // OSNumber (0 = low-active)
  static const char *const kResetGpioKey;       // OSNumber (TLMM 12)
  static const char *const kIrqGpioKey;         // OSNumber (TLMM 13)
  static const char *const kTsDimensionKey;     // OSData 2 x u32 LE
  static const char *const kLcdDimensionKey;    // OSData 2 x u32 LE

  // I2cBus-shaped surface for rmi::RmiXport<NativeQupI2c> (RmiCore.h names
  // the transport duck write/readAt). Serialized on one internal lock; the
  // slave address is the published reg value. Returns false with lastError()
  // carrying the qup::Err code.
  bool write(const uint8_t *b, unsigned len);
  bool readAt(uint8_t reg, uint8_t *buf, unsigned len);
  // Session teardown for the RMI4 error path (T1.4 API on the core).
  bool resetBus();
  unsigned lastError() const;

  IOService *probe(IOService *provider, SInt32 *score) override;
  bool start(IOService *provider) override;
  void stop(IOService *provider) override;
  void free() override;

 private:
  bool publishRmiFacts(IORegistryEntry *rmi);

  QupPorts ports;
  QupI2c<QupPorts> core{ports};  // binds after ports (declaration order)
  IOMemoryMap *seMapping = nullptr;
  IOLock *gate = nullptr;
  uint8_t slaveAddr = 0x20;      // replaced by the DT reg once published
};

#endif  // QCOMQUPI2C_NATIVEQUPI2C_H
