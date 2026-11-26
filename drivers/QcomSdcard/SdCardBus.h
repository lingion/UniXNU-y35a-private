// SPDX-License-Identifier: BSD-2-Clause-Patent
// Polling SDHCI adapter for the removable MSM8916 TF slot.
#ifndef QCOMSDCARD_SDCARDBUS_H
#define QCOMSDCARD_SDCARDBUS_H

#include <stdint.h>
#include "SdCardCore.h"

template <class IO> class SdCardBus {
  IO &io;
  uint32_t status_ = 0;
  uint32_t response_[4] = {};

  bool idle() {
    for (unsigned i = 0; i != 50000; ++i) {
      if (!(io.read32(0x24) & 3U)) return true;
      io.delay();
    }
    return false;
  }

  bool waitStatus(uint32_t mask) {
    for (unsigned i = 0; i != 50000; ++i) {
      status_ = io.read32(0x30);
      if (status_ & 0xffff8000U) return false;
      if ((status_ & mask) == mask) return true;
      io.delay();
    }
    return false;
  }

  bool waitDataRelease() {
    for (unsigned i = 0; i != 50000; ++i) {
      if (!(io.read32(0x24) & (1U << 3))) return true;
      io.delay();
    }
    return false;
  }

 public:
  explicit SdCardBus(IO &ports) : io(ports) {}

  bool cardPresent() const { return io.cardPresent(); }
  void delay() { io.delay(); }
  uint32_t response() const { return response_[0]; }

  bool command(unsigned index, uint32_t argument, sdcard::Transfer transfer,
               uint8_t *data, unsigned blocks) {
    if (!blocks || blocks > 65535 ||
        ((transfer != sdcard::TRANS_NONE) != (data != nullptr))) return false;
    if (!idle()) return false;
    io.write32(0x30, 0xffffffffU);
    io.write8(0x2e, 0xe);
    if (data) {
      io.write32(0x04, (blocks << 16) | 512U);
      io.write32(0x100, (io.read32(0x100) | (1U << 17)) & ~(1U << 19));
    }
    io.write32(0x08, argument);
    io.write16(0x0c, data ? 0x10 : 0);
    io.write16(0x0e, static_cast<uint16_t>((index << 8) | (data ? 0x3a : 0x1b)));
    if (!waitStatus(1)) return false;
    response_[0] = io.read32(0x10);
    response_[1] = io.read32(0x14);
    response_[2] = io.read32(0x18);
    response_[3] = io.read32(0x1c);
    io.write32(0x30, 1);
    if (index != 13 && (response_[0] & 0xfdffa080U)) return false;
    if (!data) return idle();
    if (!waitStatus(0x20) || !(io.read32(0x24) & (1U << 11))) return false;
    for (unsigned i = 0; i < blocks * 512; i += 4) {
      uint32_t value = io.read32(0x20);
      for (unsigned b = 0; b != 4; ++b)
        data[i + b] = static_cast<uint8_t>(value >> (8 * b));
    }
    io.write32(0x30, 0x20);
    if (!waitStatus(2) || !waitDataRelease()) return false;
    io.write32(0x30, 2);
    return idle();
  }

  bool setBusWidth4(uint16_t rca) {
    // SD ACMD6 argument 2 selects four data lines. The host-side width bit is
    // changed only after the card accepted the command.
    if (!command(55, uint32_t(rca) << 16, sdcard::TRANS_NONE, nullptr, 1) ||
        !command(6, 2, sdcard::TRANS_NONE, nullptr, 1)) return false;
    uint8_t host = io.read8(0x28);
    host = static_cast<uint8_t>((host & ~1U) | 2U);
    io.write8(0x28, host);
    return true;
  }

  uint32_t capacitySectors() const { return io.capacitySectors(response_); }
};

#endif
