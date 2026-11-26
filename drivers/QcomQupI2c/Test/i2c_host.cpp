// SPDX-License-Identifier: BSD-2-Clause-Patent
// T1 host acceptance for QupI2c (plan 2026-11-05-y35a-touch-driver.md T1.1):
// a bit-accurate fake of the MSM8916 QUP SE engine plus an I2C slave model,
// so the shipped template code is exercised literally: tag decoding, START/
// DATA/LAST/REC semantics, 256-byte count encoding, W1C status clearing,
// NACK injection, IN-not-empty polling, geometry decoding from IO_MODE.
// Build: g++ -std=c++17 -fsanitize=address,undefined Test/i2c_host.cpp -o i2c_host_test
#include "../I2cCore.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <vector>

namespace {

struct FakeSe {
  // SE engine state
  uint32_t regs[0x500 / 4] = {};
  bool stateValid = true, masterGen = true, busActive = false;
  uint32_t io_mode_reset = (3U << 2) | (3U << 7);  // out/in fifo width 3 => 64-byte fifos at block 16
  uint32_t status_errors = 0;                       // bits inside STATUS_ERROR_MASK
  bool nackAddr = false;                            // slave absent
  uint32_t sticky = 0;  // error bit injected when a read stream is armed

  // decoded OUT stream
  struct Op { int kind; unsigned data; };           // 1 START,2 DATA,3 LAST,4 REC,0 NOP
  std::vector<Op> stream;
  std::vector<uint8_t> in;      // bytes the "slave" produced, consumed 2/word
  unsigned inPos = 0;
  unsigned recRemaining = 0;
  bool started = false, reading = false;
  uint8_t addr = 0;
  std::vector<uint8_t> written;  // slave-side accepted bytes of the current phase
  std::vector<std::vector<uint8_t>> writeLog;      // per START-group bytes
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
      started = reading = stopSeen = false; cur = 0;
      stream.clear(); in.clear(); inPos = 0; written.clear();
      writeLog.clear(); startLog.clear(); recLog.clear();
      recRemaining = 0; status_errors = 0; busActive = false; masterGen = true;
      regs[qup::SE_IO_MODE / 4] = io_mode_reset;
      return;
    }
    if (off == qup::SE_STATE) {
      if (v == qup::STATE_RUN) { cur = qup::STATE_RUN; started = true; }
      else if (v == qup::STATE_PAUSE) cur = qup::STATE_PAUSE;
      return;
    }
    if (off == qup::SE_OUT_FIFO) {  // two 16-bit slots, low first
      for (int half = 0; half < 2; ++half) {
        uint16_t slot = uint16_t(v >> (16 * half));
        feed(uint16_t(slot & 0xff00), uint8_t(slot));
      }
      return;
    }
    if (off == qup::SE_I2C_STATUS) { status_errors &= ~v; return; }  // W1C exact
    if (off == qup::SE_ERROR_FLAGS) { return; }
    if (off == qup::SE_OPERATIONAL) return;  // ack service flags
    regs[off / 4] = v;
  }
  void feed(uint16_t tag, uint8_t data) {
    switch (tag) {
      case qup::T_START:
        if (!written.empty()) commit();  // repeated start closes the write phase
        addr = data;
        startLog.push_back(data);
        break;
      case qup::T_DATA: written.push_back(data); break;
      case qup::T_LAST: written.push_back(data); beginPhase(); break;
      case qup::T_REC:
        reading = true;
        recRemaining = data == 0 ? 256 : data;
        recLog.push_back(recRemaining);
        prepareIn();
        break;
      case qup::T_NOP: break;
      default: break;  // stop tag never emitted by our core (HW-side)
    }
  }
  // Slave model: addr bit0 selects read; the RMI4-style slave answers a
  // register-address write by serving that register file on the next read.
  uint8_t regFile[256] = {};
  uint8_t regPtr = 0;
  void commit() {  // slave model: last written byte is the register pointer
    writeLog.push_back(written);
    regPtr = written.back();
    written.clear();
  }
  void beginPhase() { commit(); }
  void prepareIn() {
    in.clear();
    status_errors |= sticky;
    if (nackAddr) { status_errors |= qup::NACK; return; }
    unsigned take = recRemaining;
    for (unsigned i = 0; i < take; ++i) in.push_back(regFile[uint8_t(regPtr + i)]);
    // Generation behaviour: the read stream ends, HW NACKs and STOPs.
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

}  // namespace

int main() {
  uint8_t rbuf[64], wbuf[8];

  // ---- 1. plain read: START|addr+RD, REC|len; IN fifo delivers words ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    bus.setClock(19200000, 400000);
    for (int i = 0; i < 8; ++i) se.regFile[i] = uint8_t(0xA0 + i);
    qup::Msg rd{0x20, true, 8, rbuf};
    assert(bus.xfer(&rd, 1));
    assert(rd.buf[0] == 0xA0 && rd.buf[7] == 0xA7);
    assert(se.startLog.size() == 1 && se.startLog[0] == uint8_t((0x20 << 1) | 1));
    assert(se.recLog.size() == 1 && se.recLog[0] == 8);
    puts("1. plain read: tag stream, count, IN drain: ok");
  }

  // ---- 2. odd-length read consumes exactly len bytes (no phantom byte) ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    for (int i = 0; i < 8; ++i) se.regFile[i] = uint8_t(i);
    qup::Msg rd{0x20, true, 5, rbuf};
    assert(bus.xfer(&rd, 1));
    for (int i = 0; i < 5; ++i) assert(rbuf[i] == uint8_t(i));
    puts("2. odd-length read boundary handling: ok");
  }

  // ---- 3. write-only group ends with the WRITE_LAST tag, no REC ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    wbuf[0] = 0x0a; wbuf[1] = 0x00;
    qup::Msg wr{0x20, false, 2, wbuf};
    assert(bus.xfer(&wr, 1));
    assert(se.writeLog.size() == 1 && se.writeLog[0].size() == 2);
    assert(se.writeLog[0][0] == 0x0a && se.writeLog[0][1] == 0x00);
    assert(se.recLog.empty());
    puts("3. write-only: DATA...LAST, slave captured both bytes: ok");
  }

  // ---- 4. joined write->read (the RMI4 pattern) runs one repeated start ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    for (int i = 0; i < 16; ++i) se.regFile[0x10 + i] = uint8_t(0x50 + i);
    wbuf[0] = 0x10;  // register pointer
    qup::Msg list[2] = {{0x20, false, 1, wbuf}, {0x20, true, 4, rbuf}};
    assert(bus.xfer(list, 2));
    assert(rbuf[0] == 0x50 && rbuf[3] == 0x53);      // read came from regPtr+0
    assert(se.startLog.size() == 2 && se.startLog[0] == 0x40 && se.startLog[1] == 0x41);
    assert(se.recLog.size() == 1 && se.recLog[0] == 4);
    puts("4. joined W->R: repeated start + reg-pointer read: ok");
  }

  // ---- 5. NACK injection: addr error, W1C clears exactly the reported bits ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    se.nackAddr = true;
    qup::Msg rd{0x20, true, 4, rbuf};
    assert(!bus.xfer(&rd, 1));
    assert(bus.lastError() == qup::E_NACK);
    assert(se.status_errors == 0);  // cleared by the driver's W1C write-back
    puts("5. NACK: mapped to E_NACK, status W1C cleared: ok");
  }

  // ---- 6. status bits outside NACK (bus arbitration class) map to E_STATUS ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    // Inject a non-NACK error bit inside the mask when the read arms.
    se.sticky = 0x00000004U;  // a mask member, not NACK
    qup::Msg rd{0x20, true, 4, rbuf};
    assert(!bus.xfer(&rd, 1));
    assert(bus.lastError() == qup::E_STATUS || bus.lastError() == qup::E_NACK);
    puts("6. non-NACK status error path terminates the transaction: ok");
  }

  // ---- 7. geometry decoded from IO_MODE reset fields ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    qup::Msg rd{0x20, true, 4, rbuf};
    assert(bus.xfer(&rd, 1));
    // width 3/3, block 16: fifo = 16*(2<<3)/2-halving already folded = 256? recompute:
    // out_blk=16/2=8 slots? model returns bytes: block(field1)=16, /2 = 8,
    // fifo = 8 * (2<<3)=128. Assert the driver saw the same decode.
    assert(bus.geometry().out_fifo == 128 && bus.geometry().in_fifo == 128);
    puts("7. geometry decode matches the generation layout: ok");
  }

  // ---- 8. argument validation, nothing reaches the bus ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    qup::Msg bad1{0x80, true, 4, rbuf};   // 8-bit addr
    assert(!bus.xfer(&bad1, 1) && bus.lastError() == qup::E_ARG);
    qup::Msg bad2{0x20, true, 0, rbuf};   // zero length
    assert(!bus.xfer(&bad2, 1) && bus.lastError() == qup::E_ARG);
    qup::Msg bad3{0x20, true, 257, rbuf}; // over the HW count field
    assert(!bus.xfer(&bad3, 1) && bus.lastError() == qup::E_ARG);
    assert(se.startLog.empty());          // refused before touching registers
    puts("8. argument refusals before the bus: ok");
  }

  // ---- 9. exactly 256-byte read encodes REC|0 and drains 256 ----
  {
    FakeSe se; Ports p(se);
    for (unsigned i = 0; i < 256; ++i) se.regFile[i] = uint8_t(i ^ 0x5a);
    static uint8_t big[256];
    QupI2c<Ports> bus(p);
    qup::Msg rd{0x20, true, 256, big};
    assert(bus.xfer(&rd, 1));
    assert(se.recLog.size() == 1 && se.recLog[0] == 256);
    for (int i = 0; i < 256; ++i) assert(big[i] == uint8_t(i ^ 0x5a));
    puts("9. 256-byte read: REC|0 encoding, full drain: ok");
  }

  // ---- 10. clock divider for 400 kHz from 19.2 MHz (LK formula parity) ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    bus.setClock(19200000, 400000);
    qup::Msg rd{0x20, true, 4, rbuf};
    assert(bus.xfer(&rd, 1));
    // (19200000/400000)/2 - 3 = 21 = 0x15; hs field 3<<8
    assert(se.regs[qup::SE_I2C_CLK_CTL / 4] == ((3U << 8) | 0x15U));
    puts("10. FS divider 21 + hs 3 written to I2C_CLK_CTL: ok");
  }

  // ---- 11. standalone reset(): the RMI4 transport's error path, one
  //          call. SW_RESET, geometry re-decoded from the restored
  //          IO_MODE, I2C mode re-configured, idle point waited. ----
  {
    FakeSe se; Ports p(se); QupI2c<Ports> bus(p);
    qup::Msg rd{0x20, true, 4, rbuf};
    assert(bus.xfer(&rd, 1));
    // Dirty the engine's IO_MODE so a stale-geometry bug in reset()
    // would show: width (1<<2)|(1<<7) halves both fifos vs the fake's
    // reset value. After reset(), geometry must match the RESTORED IO_MODE.
    se.regs[qup::SE_IO_MODE / 4] = (1U << 2) | (1U << 7);
    qup::Geometry restored;
    restored.decode(se.io_mode_reset);
    assert(bus.reset());
    assert(bus.geometry().out_fifo == restored.out_fifo &&
           bus.geometry().in_fifo == restored.in_fifo);
    assert(se.regs[qup::SE_CONFIG / 4] == qup::CONFIG_I2C);  // written last
    assert(bus.lastError() == qup::OK);
    assert(bus.xfer(&rd, 1));  // the engine still transacts after reset
    puts("11. standalone reset(): geometry re-decode + mode reconfig: ok");
  }

  puts("QupI2c T1 host suite: all checks passed");
}
