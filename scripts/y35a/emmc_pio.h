// SPDX-License-Identifier: BSD-2-Clause-Patent
// Experimental read-only transport for the measured LK2nd MSM8916 handoff.
// This resumes the card and controller configured by LK2nd. It is not cold init.
#ifndef Y35A_EMMC_PIO_H
#define Y35A_EMMC_PIO_H
#include <stdint.h>

template<class IO> class EmmcPio {
  IO &io;
  uint32_t capacity = 0;
  bool ready = false;
  bool waitStatus(uint32_t mask) {
    for (unsigned i = 0; i < 50000; ++i) {
      status = io.read32(0x30);
      if (status & 0xffff8000U) { error = 2; return false; }
      if ((status & mask) == mask) return true;
      io.delay();
    }
    error = 1; return false;
  }
  bool idle() {
    for (unsigned i = 0; i < 50000; ++i) {
      if (!(io.read32(0x24) & 3)) return true;
      io.delay();
    }
    error = 3; return false;
  }
  bool command(unsigned index, uint32_t argument, uint8_t *data) {
    // No write, erase, switch, partition-selection or programming commands.
    if (index != 5 && index != 7 && index != 8 && index != 17) {
      error = 4; return false;
    }
    error = 0; lastCommand = index;
    if (!idle()) return false;
    io.write32(0x30, 0xffffffffU);
    io.write8(0x2e, 0xe);
    if (data) {
      io.write16(0x04, 512);
      io.write16(0x06, 1);
      // Match LK2nd's read-side DLL policy, preserving its tuned phase.
      io.write32(0x100, (io.read32(0x100) | (1U << 17)) & ~(1U << 19));
    }
    io.write32(0x08, argument);
    io.write16(0x0c, data ? 0x10 : 0); // PIO, one block, read direction.
    io.write16(0x0e, (index << 8) | (data ? 0x3a : 0x1b));
    if (!waitStatus(1)) return false;
    response = io.read32(0x10);
    io.write32(0x30, 1);
    if (response & 0xfdffa080U) { error = 5; return false; }
    if (data) {
      if (!waitStatus(0x20)) return false;
      if (!(io.read32(0x24) & (1U << 11))) { error = 6; return false; }
      for (unsigned i = 0; i < 512; i += 4) {
        uint32_t value = io.read32(0x20);
        for (unsigned b = 0; b < 4; ++b) data[i+b] = value >> (8*b);
      }
      io.write32(0x30, 0x20);
      if (!waitStatus(2)) return false;
      io.write32(0x30, 2);
    }
    return idle();
  }
public:
  unsigned error = 0, lastCommand = 0;
  uint32_t status = 0, response = 0;
  explicit EmmcPio(IO &port) : io(port) {}
  bool resume(uint16_t rca, uint8_t *extCsd) {
    ready = false; capacity = 0;
    if (!rca || !extCsd) { error = 4; return false; }
    io.enableHostMode();
    // The bootloader owns regulator, clocks and tuning. Refuse an absent clock
    // or power supply rather than silently assuming a usable handoff.
    if ((io.read16(0x2c) & 7) != 7 || !(io.read8(0x29) & 1)) {
      error = 7; return false;
    }
    io.write32(0x38, 0); // Poll only, no CPU interrupt signal.
    io.write32(0x34, 0x03ff0033U);
    if (!command(5, uint32_t(rca) << 16, nullptr) ||
        !command(7, uint32_t(rca) << 16, nullptr) ||
        !command(8, 0, extCsd)) return false;
    // Do not expose boot partitions or RPMB as the user area.
    if (extCsd[179] & 7) { error = 8; return false; }
    capacity = uint32_t(extCsd[212]) | uint32_t(extCsd[213]) << 8 |
               uint32_t(extCsd[214]) << 16 | uint32_t(extCsd[215]) << 24;
    if (!capacity) { error = 9; return false; }
    ready = true; return true;
  }
  uint32_t sectors() const { return capacity; }
  bool read(uint32_t sector, uint8_t *data) {
    if (!ready || !data || sector >= capacity) { error = 4; return false; }
    if (command(17, sector, data)) return true;
    ready = false; // No retry against a controller left in an unknown state.
    return false;
  }
};
#endif
