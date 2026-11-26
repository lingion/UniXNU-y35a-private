// SPDX-License-Identifier: BSD-2-Clause-Patent
// Shared host model for the QUP SE I2C engine and the RMI4 page-aware
// slave, extracted from the T1 suite (Test/i2c_host.cpp of commit
// 054915a) so QcomTouch tests exercise the literal transport stack:
// QupI2c<Ports> -> FakeSe -> RmiSlave. One fake, both drivers, no
// copy-paste divergence (plan 2026-11-05-y35a-touch-driver.md T2.1).
//
// The slave model implements the Synaptics device-pointer semantics the
// v4.9 rmi_i2c transport depends on:
//   - a write transaction's first byte is the register address; the
//     16-bit device pointer = (page<<8 | byte), then auto-increments
//     across page edges for the remaining bytes (rmi_i2c.c:130-166 relies
//     on the auto-incrementing stream, and rmi_set_page re-syncs after
//     writes that cross, rmi_i2c.c write_block tail);
//   - a standalone {0xff,page} write is the page select (rmi_i2c.c:64-77),
//     moving the pointer to (page<<8)|0xff;
//   - reads stream from the current pointer without re-addressing.
#ifndef RMI_MODEL_H
#define RMI_MODEL_H

#include "../I2cCore.h"
#include <stdint.h>
#include <string.h>
#include <vector>

namespace model {

struct RmiSlave {
  static constexpr unsigned REGFILE = 4096;  // 16 pages for tests
  uint8_t regfile[REGFILE] = {};
  uint16_t devPtr = 0;                       // device-side auto ptr
  // stats the tests assert on
  unsigned reads = 0, writes = 0, pageSelects = 0;
  std::vector<std::vector<uint8_t>> writeLog;
  bool nack = false;              // slave absent: NACK every transaction

  void poke(uint16_t addr, const void *data, unsigned len) {
    memcpy(&regfile[addr & (REGFILE - 1)], data, len);
  }
  void poke8(uint16_t addr, uint8_t v) { regfile[addr & (REGFILE - 1)] = v; }

  // Synaptics pointer semantics (v4.9 rmi_i2c.c:130-166 relies on them):
  // a write phase's first byte is the register address on the CURRENT
  // page; data lands at (page<<8|byte0)+1.. and the pointer ends at the
  // last placed byte. A joined [W:addr][R:len] read therefore starts at
  // the address byte itself and auto-increments; a following standalone
  // read continues from wherever the pointer was left.
  void writeStream(const uint8_t *b, unsigned len) {
    if (nack) return;  // engine-side NACK recorded by the caller
    ++writes;
    writeLog.push_back(std::vector<uint8_t>(b, b + len));
    if (b[0] == 0xff && len == 2) {  // rmi_set_page {0xff,page}
      devPtr = uint16_t((uint16_t(b[1]) << 8) | 0xff);
      ++pageSelects;
      return;
    }
    uint16_t p = uint16_t((devPtr & 0xff00) | b[0]);  // address byte:
    // data bytes auto-increment; overflow past 0xff stays ON the
    // selected page (the page register only changes via {0xff,page}),
    // so the low byte wraps: (page<<8)|0xff + 1 -> (page<<8)|0x00.
    for (unsigned i = 1; i < len; ++i) {
      regfile[p & (REGFILE - 1)] = b[i];
      p = uint16_t((p & 0xff00) | ((p + 1) & 0xff));
    }
    devPtr = p;  // len==1 leaves p AT the address byte: the joined
                 // [W addr][R len] read begins exactly there
                 // (repeated start, no data written). len>1 leaves it
                 // one past the last placed byte, page-preserving.
  }
  void readStream(unsigned take, std::vector<uint8_t> &out) {
    if (nack) return;
    ++reads;
    uint16_t p = devPtr;
    for (unsigned i = 0; i < take; ++i) {
      out.push_back(regfile[p & (REGFILE - 1)]);
      p = uint16_t((p & 0xff00) | ((p + 1) & 0xff));  // wrap in-page
    }
    devPtr = p;  // auto-increment survives reads too
  }
};

struct FakeSe {
  RmiSlave &slave;
  explicit FakeSe(RmiSlave &s) : slave(s) {}

  uint32_t regs[0x500 / 4] = {};
  bool stateValid = true, masterGen = true, busActive = false;
  uint32_t io_mode_reset =
      (3U << 2) | (3U << 7);  // out/in fifo width 3 => 64-byte fifos at block 16
  uint32_t status_errors = 0;  // bits inside STATUS_ERROR_MASK
  uint32_t sticky = 0;         // error bit injected when a read is armed

  struct Op {
    int kind;
    unsigned data;
  };  // 1 START,2 DATA,3 LAST,4 REC,0 NOP
  std::vector<Op> stream;
  std::vector<uint8_t> in;  // bytes the "slave" produced, consumed 2/word
  unsigned inPos = 0;
  unsigned recRemaining = 0;
  bool started = false, reading = false;
  uint8_t addr = 0;
  std::vector<uint8_t> written;         // bytes of the current phase
  std::vector<unsigned> startLog, recLog;
  bool stopSeen = false;

  unsigned cur = 0;  // 0 idle (MASTER_GEN pending), RUN/PAUSE as commanded
  uint32_t read32(unsigned off) {
    if (off == qup::SE_STATE) {
      uint32_t base = (stateValid ? qup::STATE_VALID : 0) | cur;
      if (cur == 0 && masterGen) base |= qup::MASTER_GEN;
      return base;
    }
    if (off == qup::SE_IO_MODE) return regs[off / 4];
    if (off == qup::SE_OPERATIONAL) {
      uint32_t v = 0;
      if (inPos < in.size()) v |= qup::IN_NOT_EMPTY;
      if (reading && inPos >= in.size() && recRemaining == 0) v |= qup::IN_DONE;
      return v;
    }
    if (off == qup::SE_ERROR_FLAGS) return 0;
    if (off == qup::SE_I2C_STATUS) {
      uint32_t v = status_errors | (busActive ? qup::BUS_ACTIVE : 0);
      return v;
    }
    if (off == qup::SE_IN_FIFO) {
      uint32_t w = 0;
      if (inPos < in.size()) w = in[inPos++];
      if (inPos < in.size()) w |= uint32_t(in[inPos++]) << 16;
      return w;
    }
    return regs[off / 4];
  }
  void write32(unsigned off, uint32_t v) {
    if (off == qup::SE_SW_RESET) {
      started = reading = stopSeen = false;
      cur = 0;
      stream.clear();
      in.clear();
      inPos = 0;
      written.clear();
      startLog.clear();
      recLog.clear();
      recRemaining = 0;
      status_errors = 0;
      busActive = false;
      masterGen = true;
      regs[qup::SE_IO_MODE / 4] = io_mode_reset;
      return;
    }
    if (off == qup::SE_STATE) {
      if (v == qup::STATE_RUN) {
        cur = qup::STATE_RUN;
        started = true;
      } else if (v == qup::STATE_PAUSE)
        cur = qup::STATE_PAUSE;
      return;
    }
    if (off == qup::SE_OUT_FIFO) {  // two 16-bit slots, low first
      for (int half = 0; half < 2; ++half) {
        uint16_t slot = uint16_t(v >> (16 * half));
        feed(uint16_t(slot & 0xff00), uint8_t(slot));
      }
      return;
    }
    if (off == qup::SE_I2C_STATUS) {
      status_errors &= ~v;
      return;
    }  // W1C exact
    if (off == qup::SE_ERROR_FLAGS) {
      return;
    }
    if (off == qup::SE_OPERATIONAL) return;  // ack service flags
    regs[off / 4] = v;
  }
  void feed(uint16_t tag, uint8_t data) {
    switch (tag) {
      case qup::T_START:
        if (!written.empty()) commit();  // repeated start closes the phase
        addr = data;
        startLog.push_back(data);
        break;
      case qup::T_DATA:
        written.push_back(data);
        break;
      case qup::T_LAST:
        written.push_back(data);
        beginPhase();
        break;
      case qup::T_REC:
        reading = true;
        recRemaining = data == 0 ? 256 : data;
        recLog.push_back(recRemaining);
        prepareIn();
        break;
      case qup::T_NOP:
        break;
      default:
        break;  // stop tag never emitted by our core (HW-side)
    }
  }
  void commit() {
    if (slave.nack) {
      status_errors |= qup::NACK;
      written.clear();
      return;
    }
    slave.writeStream(written.data(), unsigned(written.size()));
    written.clear();
  }
  void beginPhase() { commit(); }
  void prepareIn() {
    in.clear();
    status_errors |= sticky;
    if (slave.nack) {
      status_errors |= qup::NACK;
      return;
    }
    // The read stream starts at the latched pointer: a joined group's
    // address byte left devPtr exactly there; a standalone read follows
    // whatever the previous transaction ended on.
    slave.readStream(recRemaining, in);
    recRemaining = 0;
    busActive = false;
  }
  void delay() {}
};

struct Ports {
  FakeSe &se;
  explicit Ports(FakeSe &s) : se(s) {}
  uint32_t read32(unsigned off) { return se.read32(off); }
  void write32(unsigned off, uint32_t v) { se.write32(off, v); }
  void delay() { se.delay(); }
};

// Bus adapter the RmiXport template ducks against: exactly the two
// primitives v4.9 rmi_i2c.c builds its read_block/write_block from.
struct I2cBus {
  static constexpr uint16_t SLAVE_ADDR = 0x20;
  QupI2c<Ports> &i2c;
  explicit I2cBus(QupI2c<Ports> &b) : i2c(b) {}
  bool write(const uint8_t *b, unsigned len) {
    qup::Msg m{SLAVE_ADDR, false, uint16_t(len), const_cast<uint8_t *>(b)};
    return i2c.xfer(&m, 1);
  }
  bool readAt(uint8_t reg, uint8_t *buf, unsigned len) {
    qup::Msg list[2] = {{SLAVE_ADDR, false, 1, &reg},
                        {SLAVE_ADDR, true, uint16_t(len), buf}};
    return i2c.xfer(list, 2);
  }
};

}  // namespace model

#endif  // RMI_MODEL_H
