// SPDX-License-Identifier: BSD-2-Clause-Patent
// SD-card protocol core for the MSM8916 sdhc2 removable TF slot.
// The bus adapter owns SDHCI register encoding; this header owns the
// card-level command sequence and LBA addressing rules.
#ifndef QCOMSDCARD_SDCARDCORE_H
#define QCOMSDCARD_SDCARDCORE_H

#include <stdint.h>

namespace sdcard {

enum Transfer : uint8_t {
  TRANS_NONE = 0,
  TRANS_READ = 1,
};

struct CardInfo {
  uint16_t rca = 0;
  uint32_t ocr = 0;
  uint32_t sectors = 0;
  bool high_capacity = false;
  bool four_bit = false;
};

template <class BUS> class Controller {
  BUS &bus;
  CardInfo info_;
  bool ready_ = false;

  bool appCommand() {
    return bus.command(55, uint32_t(info_.rca) << 16, TRANS_NONE, nullptr, 1);
  }

  bool waitReady() {
    // The SD specification permits the card to remain busy while it powers
    // up. The adapter supplies a bounded command timeout; this loop adds a
    // bounded protocol retry count and never waits indefinitely.
    for (unsigned attempt = 0; attempt != 100; ++attempt) {
      if (!appCommand()) return false;
      if (!bus.command(41, 0x40ff8000U, TRANS_NONE, nullptr, 1)) return false;
      info_.ocr = bus.response();
      if (info_.ocr & 0x80000000U) {
        info_.high_capacity = (info_.ocr & 0x40000000U) != 0;
        return true;
      }
      bus.delay();
    }
    return false;
  }

  uint32_t address(uint32_t sector) const {
    return info_.high_capacity ? sector : sector * 512U;
  }

 public:
  unsigned error = 0;

  explicit Controller(BUS &adapter) : bus(adapter) {}

  bool init() {
    ready_ = false;
    info_ = {};
    error = 0;
    if (!bus.cardPresent()) { error = 1; return false; }
    if (!bus.command(0, 0, TRANS_NONE, nullptr, 1)) { error = 2; return false; }
    if (!bus.command(8, 0x1aaU, TRANS_NONE, nullptr, 1) ||
        (bus.response() & 0xfffU) != 0x1aaU) { error = 3; return false; }
    if (!waitReady()) { error = 4; return false; }
    if (!bus.command(2, 0, TRANS_NONE, nullptr, 1)) { error = 5; return false; }
    if (!bus.command(3, 0, TRANS_NONE, nullptr, 1)) { error = 6; return false; }
    info_.rca = static_cast<uint16_t>(bus.response() >> 16);
    if (!info_.rca) { error = 7; return false; }
    if (!bus.command(9, uint32_t(info_.rca) << 16, TRANS_NONE, nullptr, 1)) {
      error = 8; return false;
    }
    if (!bus.command(7, uint32_t(info_.rca) << 16, TRANS_NONE, nullptr, 1)) {
      error = 9; return false;
    }
    if (!bus.setBusWidth4(info_.rca)) { error = 10; return false; }
    info_.four_bit = true;
    if (!info_.high_capacity &&
        !bus.command(16, 512, TRANS_NONE, nullptr, 1)) {
      error = 11; return false;
    }
    info_.sectors = bus.capacitySectors();
    if (!info_.sectors) { error = 12; return false; }
    ready_ = true;
    return true;
  }

  bool readSectors(uint32_t start, unsigned count, uint8_t *data) {
    if (!ready_ || !data || !count || uint64_t(start) + count > info_.sectors) {
      error = 12; return false;
    }
    if (count == 1) {
      if (!bus.command(17, address(start), TRANS_READ, data, 1)) {
        error = 13; return false;
      }
      return true;
    }
    if (!bus.command(18, address(start), TRANS_READ, data, count)) {
      error = 14; return false;
    }
    if (!bus.command(12, 0, TRANS_NONE, nullptr, 1)) {
      error = 15; return false;
    }
    return true;
  }

  const CardInfo &info() const { return info_; }
  bool ready() const { return ready_; }
};

} // namespace sdcard

#endif
