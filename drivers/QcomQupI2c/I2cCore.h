// SPDX-License-Identifier: BSD-2-Clause-Patent
// QUP SE-mode I2C transaction core for the MSM8916 BLSP1 QUP5 (i2c@78b9000,
// vivo Y35A touch bus). The register map, tag semantics and the
// RUN/PAUSE/refill discipline are re-expressed from this SoC generation's
// public register layout, cross-checked against the sequence lk2nd
// demonstrably runs on this phone (platform/msm_shared/i2c_qup.c read in
// full on 2026-11-05); bit knowledge only, no code copied — clean room.
// Facts: docs/board/y35a-facts.md Touch section; plan
// docs/superpowers/plans/2026-11-05-y35a-touch-driver.md T1.
//
// Polled, SE-mode, PIO only — no BAM (touch frames are small; PIO keeps the
// coherency surface at zero, the same discipline as SdciCore's PIO phases).
// template<class IO> so the exact code runs in host model tests and in the
// kernel driver.
//
// OUT FIFO slot tags (16-bit each, packed two per 32-bit word, low first):
//   0 NOP | 1 START(addr in byte) | 2 DATA(byte) | 3 WRITE_LAST(byte+STOP)
//   4 READ(count; 0 encodes 256) — the stream after READ is hardware-driven
//   and terminates with NACK+STOP.
// IN FIFO words: [15:0] byte+tag(5), [31:16] next byte+tag; odd tails leave
// the high byte undefined — never consume it.
//
// T1 scope: SE plain mode and read block mode. A write stream that would
// exceed the plain OUT fifo (msg.len >= out_fifo - 1, the generation's own
// block-mode trigger) refuses with E_ARG — the RMI4 traffic this driver
// exists for never builds such writes (register payloads are ≤64 B).
#ifndef QCOMQUPI2C_I2CCORE_H
#define QCOMQUPI2C_I2CCORE_H
#include <stdint.h>

namespace qup {

enum : unsigned {  // SE window (0x78b9000, len 0x600) relative offsets
  SE_CONFIG = 0x000, SE_STATE = 0x004, SE_IO_MODE = 0x008, SE_SW_RESET = 0x00c,
  SE_OPERATIONAL = 0x018, SE_ERROR_FLAGS = 0x01c, SE_ERROR_FLAGS_EN = 0x020,
  SE_MX_WR_CNT = 0x100, SE_OUT_FIFO = 0x110,
  SE_MX_INPUT_CNT = 0x200, SE_MX_READ_CNT = 0x208, SE_IN_FIFO = 0x218,
  SE_I2C_CLK_CTL = 0x400, SE_I2C_STATUS = 0x404,
};
constexpr uint32_t STATE_RUN = 1, STATE_PAUSE = 3, STATE_VALID = 1U << 2,
                   MASTER_GEN = 1U << 4;
constexpr uint32_t OUT_SVC = 1U << 8, IN_SVC = 1U << 9, IN_DONE = 1U << 11,
                   IN_NOT_EMPTY = 1U << 5;
constexpr uint32_t WR_BUFFER_FULL = 1U << 0, BUS_ACTIVE = 1U << 8,
                   STATUS_ERROR_MASK = 0x38000fcU, NACK = 1U << 3;
constexpr uint32_t WR_BLK = 1U << 10, RD_BLK = 1U << 12, PACK_EN = 1U << 15,
                   UNPACK_EN = 1U << 14;
constexpr uint32_t CONFIG_I2C = (2U << 8) | 0xf;  // I2C mini core, N=15
enum Tag : uint16_t { T_NOP = 0, T_START = 1U << 8, T_DATA = 2U << 8,
                      T_LAST = 3U << 8, T_REC = 4U << 8 };
constexpr uint32_t STATUS_CLEAR = 0xfffffcU, OPER_CLEAR = 0xff0U;

struct Msg {
  uint16_t addr;  // 7-bit
  bool read;
  uint16_t len;
  uint8_t *buf;
};

enum Err : unsigned {
  OK = 0, E_ARG = 1, E_NACK = 2, E_STATUS = 3, E_TIMEOUT_STATE = 4,
  E_TIMEOUT_IN = 5, E_TIMEOUT_BUS = 6,
};

// Data-byte capacities decoded from the IO_MODE reset fields (block = 16 x
// field-or-1 halved for tag overhead; fifo = block x the 3-bit width shift).
struct Geometry {
  unsigned out_fifo = 16, in_fifo = 16;
  void decode(uint32_t io_mode) {
    unsigned ob = ((io_mode & 3) ? (io_mode & 3) : 1) * 16 / 2;
    unsigned ib = ((io_mode & (3U << 5)) ? (io_mode >> 5) & 3 : 1) * 16 / 2;
    out_fifo = ob * (2U << ((io_mode >> 2) & 7));
    in_fifo = ib * (2U << ((io_mode >> 7) & 7));
  }
};

}  // namespace qup

template <class IO> class QupI2c {
  IO &io;
  qup::Geometry geo;
  uint32_t clk_ctl = 0;
  unsigned out_slot = 0;
  uint32_t pending = 0, pending_bits = 0;
  unsigned error = qup::OK;

  uint32_t op() const { return io.read32(qup::SE_OPERATIONAL); }
  uint32_t status() const { return io.read32(qup::SE_I2C_STATUS); }
  bool pollState(uint32_t want) {
    // Generation semantics (LK parity): the polled bit(s) are exactly
    // VALID|want — works for state bits (RUN/PAUSE/idle) and for the
    // MASTER_GEN bit the init path waits on.
    for (unsigned i = 0; i < 20000; ++i) {
      uint32_t s = io.read32(qup::SE_STATE);
      if ((s & (qup::STATE_VALID | want)) == (qup::STATE_VALID | want)) return true;
      io.delay();
    }
    error = qup::E_TIMEOUT_STATE; return false;
  }
  bool setState(uint32_t want) {
    if (!pollState(0)) return false;  // every transition needs a valid idle point
    io.write32(qup::SE_STATE, want);
    return pollState(want);
  }
  // Status error bits must be cleared by writing back exactly the reported
  // set (W1C), or the next transaction starts already "failed".
  bool checkStatus() {
    uint32_t s = status() & qup::STATUS_ERROR_MASK;
    if (!s) return true;
    io.write32(qup::SE_I2C_STATUS, s);
    io.write32(qup::SE_ERROR_FLAGS, io.read32(qup::SE_ERROR_FLAGS) & 0x7f);
    error = (s & qup::NACK) ? qup::E_NACK : qup::E_STATUS;
    return false;
  }
  bool waitBusIdle() {
    for (unsigned i = 0; i < 40000; ++i) {
      if (!checkStatus()) return false;
      if (!(status() & qup::BUS_ACTIVE)) return true;
      io.delay();
    }
    error = qup::E_TIMEOUT_BUS; return false;
  }
  void slot(uint16_t v) {
    pending |= uint32_t(v) << pending_bits;
    pending_bits += 16;
    if (pending_bits == 32) { io.write32(qup::SE_OUT_FIFO, pending); pending = 0; pending_bits = 0; }
    out_slot += 2;
  }
  void flush() {
    if (pending_bits) { io.write32(qup::SE_OUT_FIFO, pending); pending = 0; pending_bits = 0; }
  }

 public:
  explicit QupI2c(IO &port) : io(port) {}
  unsigned lastError() const { return error; }
  const qup::Geometry &geometry() const { return geo; }

  // Standalone session teardown: one SW_RESET write, wait for the idle
  // point, re-decode geometry. Same bring-up the transaction path runs,
  // without starting a transaction (the RMI4 transport's error path:
  // after a failed read the caller resets the engine before re-arming).
  bool reset() {
    error = qup::OK;
    io.write32(qup::SE_SW_RESET, 1);
    if (!pollState(0)) return false;
    geo.decode(io.read32(qup::SE_IO_MODE));
    io.write32(qup::SE_CONFIG, 0);
    io.write32(qup::SE_OPERATIONAL, qup::OPER_CLEAR);
    io.write32(qup::SE_CONFIG, qup::CONFIG_I2C);
    if (!pollState(qup::MASTER_GEN)) return false;
    return true;
  }

  // Legacy FS divider for the master core: fs_div = (src/hz)/2 - 3, hs_div 3
  // — the encoding the boot stack on this SoC generation runs. The DT's
  // fs-clk-div/high-time-clk-div pair belongs to the Linux MTS path, not
  // this register; T0 verifies 400 kHz on the wire.
  void setClock(uint32_t src_hz, uint32_t bus_hz) {
    clk_ctl = (3U << 8) | (((src_hz / bus_hz) / 2 - 3) & 0xffU);
  }

  // A write immediately followed by a same-address read joins into ONE
  // bus transaction with a repeated start (the RMI4 pattern: write register
  // address, Sr, read payload). Other messages run standalone.
  bool xfer(qup::Msg *msgs, unsigned num) {
    if (!num || num > 8) { error = qup::E_ARG; return false; }
    for (unsigned i = 0; i < num; ++i) {
      const qup::Msg &m = msgs[i];
      if (m.addr > 0x7f || !m.len || !m.buf || (m.read && m.len > 256)) {
        error = qup::E_ARG; return false;
      }
    }
    if (!init()) return false;
    for (unsigned i = 0; i < num; ) {
      const bool join = !msgs[i].read && i + 1 < num &&
                        msgs[i + 1].read && msgs[i + 1].addr == msgs[i].addr;
      if (!group(msgs[i], join ? &msgs[i + 1] : nullptr)) return false;
      i += join ? 2 : 1;
    }
    return true;
  }

 private:
  // One SW_RESET bring-up per transaction list, like the boot stack:
  // repeated starts ride the same session.
  bool init() {
    error = qup::OK;
    io.write32(qup::SE_SW_RESET, 1);
    if (!pollState(0)) return false;
    geo.decode(io.read32(qup::SE_IO_MODE));
    io.write32(qup::SE_CONFIG, 0);
    io.write32(qup::SE_OPERATIONAL, qup::OPER_CLEAR);
    io.write32(qup::SE_ERROR_FLAGS, 0x7f);
    io.write32(qup::SE_ERROR_FLAGS_EN, 0x7c);
    io.write32(qup::SE_CONFIG, qup::CONFIG_I2C);
    io.write32(qup::SE_I2C_CLK_CTL, 0);
    io.write32(qup::SE_I2C_STATUS, qup::STATUS_CLEAR);
    if (!pollState(qup::MASTER_GEN)) return false;
    return true;
  }

  bool group(qup::Msg &w, qup::Msg *rd) {
    if (rd && rd->len > 256) { error = qup::E_ARG; return false; }
    // Plain-mode capacity: START + write bytes (+START+REC for a read tail).
    unsigned stream = w.read ? 2 : w.len + 1 + (rd ? 2 : 0);
    if (!w.read && w.len >= geo.out_fifo - 1) { error = qup::E_ARG; return false; }  // generation's block-mode trigger
    if (stream > geo.out_fifo) { error = qup::E_ARG; return false; }
    if (rd && w.read && stream != 2) { error = qup::E_ARG; return false; }  // reads are always the group head

    if (!pollState(qup::MASTER_GEN)) return false;
    if (rd) {  // read side first: program mode + count, then the stream
      if (rd->len <= geo.in_fifo) {
        io.write32(qup::SE_IO_MODE, qup::PACK_EN | qup::UNPACK_EN);
        io.write32(qup::SE_MX_READ_CNT, rd->len);
      } else {
        io.write32(qup::SE_IO_MODE, qup::RD_BLK | qup::PACK_EN | qup::UNPACK_EN);
        io.write32(qup::SE_MX_INPUT_CNT, rd->len);
      }
    } else
      io.write32(qup::SE_IO_MODE, qup::PACK_EN | qup::UNPACK_EN);

    if (!setState(qup::STATE_RUN)) return false;
    io.write32(qup::SE_I2C_CLK_CTL, clk_ctl);
    if (!setState(qup::STATE_PAUSE)) return false;
    out_slot = 0; pending = 0; pending_bits = 0;

    if (w.read) {
      slot(uint16_t(qup::T_START | ((w.addr << 1) | 1)));
      slot(uint16_t(qup::T_REC | (w.len == 256 ? 0 : w.len)));
      rd = &w;  // pure read group: the head IS the read tail
    } else {
      slot(uint16_t(qup::T_START | uint16_t(w.addr << 1)));
      for (unsigned b = 0; b < w.len; ++b)
        slot(rd || b + 1 < w.len ? uint16_t(qup::T_DATA | w.buf[b])
                                 : uint16_t(qup::T_LAST | w.buf[b]));
      if (rd) {  // joined: repeated start, stream ends after REC via HW NACK+STOP
        slot(uint16_t(qup::T_START | ((rd->addr << 1) | 1)));
        slot(uint16_t(qup::T_REC | (rd->len == 256 ? 0 : rd->len)));
      }
    }
    flush();
    if (!setState(qup::STATE_RUN)) return false;

    if (rd) return drain(*rd) && waitBusIdle();
    return waitBusIdle();
  }

  // Drain exactly len bytes, word by word; the high byte is real only for
  // even continuation positions and is discarded at an odd tail.
  bool drain(qup::Msg &rd) {
    unsigned want = rd.len, got = 0, idle_polls = 0;
    while (got < want) {
      if (!checkStatus()) return false;
      bool ready = false;
      while (!ready) {
        ready = (op() & qup::IN_NOT_EMPTY) != 0;
        if (ready) break;
        if (!checkStatus()) return false;
        if (++idle_polls > 100000) { error = qup::E_TIMEOUT_IN; return false; }
        io.delay();
      }
      uint32_t word = io.read32(qup::SE_IN_FIFO);
      rd.buf[got++] = uint8_t(word);
      if (got < want) rd.buf[got++] = uint8_t(word >> 16);
      io.write32(qup::SE_OPERATIONAL, qup::IN_SVC);
    }
    return true;
  }
};

#endif
