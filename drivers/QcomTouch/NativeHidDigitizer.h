// SPDX-License-Identifier: BSD-2-Clause-Patent
// NativeHidDigitizer — IOHIDDevice shell for the Synaptics S3202 (RMI4) on
// the NativeQupI2c bus (personality T4.2 entry 2: IOProviderClass =
// NativeQupI2c). handleStart runs the REAL bring-up sequence from
// DigitizerBoot.h over rmi::RmiXport<NativeQupI2c>; the base class then
// fetches the static MT1-style report descriptor (newReportDescriptor),
// publishes HID properties and registerService()s (the 1090.270.6 start
// flow documented in the certified shim). Each frame path is polled
// attention (no IRQ registration in T3.2; T5 owns that): decode through
// RmiCore, pack the MT1 blob, publish the snapshot under one IOLock.
//
// Shim dialect: IOHIDFamily 1090.270.6 headers in build/hid-abi/include
// (certified T3.1). publishReport-style later-generation APIs and
// OSSharedPtr do NOT exist here; signatures verbatim from the shim.
#ifndef QCOMTOUCH_NATIVEHIDDIGITIZER_H
#define QCOMTOUCH_NATIVEHIDDIGITIZER_H

#include <IOKit/IOLocks.h>
#include <IOKit/hid/IOHIDDevice.h>

#include "DigitizerBoot.h"

class NativeQupI2c;

class NativeHidDigitizer : public IOHIDDevice {
  OSDeclareDefaultStructors(NativeHidDigitizer)

 public:
  // Input report geometry = the MT1 blob exactly (DigitizerBoot.h):
  // [0] contact count, then five 7-byte slots {index, x LE16, y LE16, z,
  // flags(bit0 tipswitch, bit1 confidence)}.
  static constexpr unsigned kReportBytes = digitizerboot::kBlobBytes;

  IOService *probe(IOService *provider, SInt32 *score) override;
  bool start(IOService *provider) override;
  void stop(IOService *provider) override;
  void free() override;

  IOReturn newReportDescriptor(IOMemoryDescriptor **descriptor) const override;

  // Polled attention intake. Returns false on transport failure (error is
  // readable via bus->lastError(); the caller may issue resetBus()).
  bool pollFrame();
  // Copy the consistent snapshot under the gate; returns byte length.
  unsigned snapshot(uint8_t *out, unsigned outLen) const;

 protected:
  // The bring-up sequence runs here, before the base class fetches the
  // report descriptor (shym IOHIDDevice.h handleStart contract).
  bool handleStart(IOService *provider) override;

 private:
  NativeQupI2c *bus = nullptr;  // borrowed from the attach (provider())
  digitizerboot::Config cfg;
  digitizerboot::Result boot;
  uint8_t *pkt = nullptr;             // attention window staging (256 cap)
  uint8_t report[kReportBytes] = {};  // current input report, under gate
  IOLock *gate = nullptr;
  bool online = false;
};

#endif  // QCOMTOUCH_NATIVEHIDDIGITIZER_H
