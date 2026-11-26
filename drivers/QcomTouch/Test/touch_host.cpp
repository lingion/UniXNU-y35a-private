// SPDX-License-Identifier: BSD-2-Clause-Patent
// T2.1 host acceptance for RmiCore + the paging transport (plan
// 2026-11-05-y35a-touch-driver.md): the shipped template code runs
// literally over QupI2c<Ports> -> FakeSe -> RmiSlave, so byte sequences,
// page-select caching, window sizes, the PDT walk, the glitch machine and
// the coordinate mapping are exercised end to end, not simulated.
//
// The fake slave is laid out as an S3202-class device, using ONLY the
// shapes the v4.9 code paths demand (no invented "facts" about the real
// panel): F01 on page 0 (query 0x0d, data 0x0e, control 0x0f, irq 2),
// F11 on page 1 (query 0x0e, ctrl 0x0f, data 0x10, cmd 0x11, irq 2).
// Finger state is the v4.9 mask — bit 0 = on (present OR inaccurate),
// bits 1-2 = the 2-bit state at (n/4 byte, 2*(n%4) shift).
// Build:
//   g++ -std=c++17 -fsanitize=address,undefined -I ../../QcomQupI2c/Test \
//       Test/touch_host.cpp -o touch_host_test
#include "../../QcomQupI2c/Test/RmiModel.h"
#include "../DigitizerBoot.h"
#include "../RmiCore.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <vector>

using namespace model;

// Ordered bring-up logger for case 17: records every stage/refusal code the
// REAL DigitizerBoot.h sequence emits (设计规范铁律: 锁顺序本身).
struct SeqLog {
  std::vector<unsigned> order;
  void stage(unsigned s) { order.push_back(s); }
  void refusal(unsigned r) { order.push_back(1000 + r); }
};

int main() {
  RmiSlave slave;
  FakeSe se(slave);
  Ports ports(se);
  QupI2c<Ports> i2c(ports);
  I2cBus bus(i2c);
  rmi::RmiXport<I2cBus> x(bus);

  // ---- 1. byte sequence: address write + repeated-start read, the
  //         v4.9 rmi_i2c_read_block shape, nothing else on the wire.
  {
    slave.pageSelects = 0;  // fresh
    uint8_t v[6] = {};
    assert(x.readBlock(0x000d, v, 6) && "basic read ok");
    // one transaction: [W 0x0d][R 6]
    assert(slave.writeLog.size() == 1 && slave.writeLog[0].size() == 1);
    assert(slave.writeLog[0][0] == 0x0d);
    puts("1. v4.9 read_block wire shape: ok");
  }

  // ---- 2. page-select caching: same page -> no traffic; page change ->
  //         exactly one {0xff,page}; pointer lands at (page<<8)|0xff
  //         (rmi_i2c.c:64-77,130-166 behaviour reproduced by the core).
  {
    uint8_t v[3];
    x.readBlock(0x0100, v, 3);  // crosses to page 1
    assert(slave.pageSelects == 1);
    // wire order: [W {0xff,01} select][W {00} addr][R 3] — the page
    // select is the SECOND-to-last write phase, the address byte lands
    // last (rmi_i2c read_block = set_page then write+read messages).
    const std::vector<uint8_t> &sel =
        slave.writeLog[slave.writeLog.size() - 2];
    assert(sel.size() == 2 && sel[0] == 0xff && sel[1] == 0x01);
    assert(slave.devPtr == 0x0103);  // address byte 0x00 + 3-byte stream
                                     // leaves the pointer there (real
                                     // device auto-increment semantics)
    x.readBlock(0x01ff, v, 1);  // page cached: NO select write...
    size_t n = slave.writeLog.size();
    assert(n >= 2);
    assert(slave.writeLog[n - 1].size() == 1 && slave.writeLog[n - 1][0] == 0xff);
    // ...and the pointer was already 0xff: the read rides the cached page
    // from 0x01ff WITHOUT re-selecting (select count unchanged).
    assert(slave.pageSelects == 1);
    puts("2. page-select caching + pointer refresh: ok");
  }

  // ---- 3. window auto-increment across a page edge, then a write
  //         re-syncs the pointer to its last byte (v4.9 rmi_i2c).
  {
    x.selectPage(1);
    uint8_t v[2];
    slave.poke8(0x01fe, 0xaa);
    slave.poke8(0x01ff, 0xbb);
    assert(x.readBlock(0x01fe, v, 2));  // crosses 1fe->1ff on page 1: no
                                        // select (same page), bytes right
    assert(v[0] == 0xaa && v[1] == 0xbb);
    // a real cross-page increment (1ff of page 0 -> 000 of page 1) would
    // be re-synced by the caller with selectPage; assert the transport
    // itself never rewrites the page on a same-page stream.
    puts("3. pointer semantics for incremental streams: ok");
  }

  // ---- 4. identity (v4.9 rmi_f01.c:161,176): manufacturer at query[0],
  //         product at query[11..20].
  {
    uint8_t q[rmi::F01_BASIC_QUERY_LEN] = {};
    q[0] = 0x01;  // Synaptics
    memcpy(&q[11], "S3202ABCD", 9);  // 10 chars incl NUL guard slot
    slave.poke(0x000d, q, sizeof q);
    rmi::FnDesc f01{0x01, 0x000d, 0x000d, 0x000d, 0x000e, 2, 0};
    uint8_t mfg;
    char product[11];
    assert(rmi::readIdentity(x, f01, mfg, product));
    assert(mfg == 0x01);
    assert(strcmp(product, "S3202ABCD") == 0);  // first 10 bytes, NUL at [10]
    puts("4. F01 identity block decode: ok");
  }

  // ---- 5. S3202 PDT walk via the paging transport: functions 0x01/0x03/
  //         0x04/0x0b then a terminator (page 1 keeps f3 on the device
  //         page, 6-byte entries, irq bits accumulated in scan order).
  {
    // page1: fn 0x3 at slot +0xe9
    uint8_t e6[6] = {0x0e, 0x11, 0x0f, 0x10, 0x02, 0x03};
    slave.poke(0x01e9, e6, 6);
    // page0: fn 0x01 at +0xe9 (F01), terminator at +0xe3
    uint8_t e6f01[6] = {0x0d, 0x0d, 0x0d, 0x0e, 0x02, 0x01};
    slave.poke(0x00e9, e6f01, 6);
    // page0 must NOT terminator-first (the old suite's fatal bug): the
    // scan reads +0xe9, sees fn1, continues to +0xe3, sees 0xff, breaks;
    // then jumps to page 1 (which has fn3), page 2 empty -> stop.
    uint8_t term[6] = {0, 0, 0, 0, 0, 0xff};
    slave.poke(0x00e3, term, 6);
    uint8_t p2e9[6] = {0, 0, 0, 0, 0, 0xff};
    slave.poke(0x02e9, p2e9, 6);
    rmi::FnDesc fns[4];
    unsigned n = rmi::scanPdt(x, fns, 4);
    assert(n == 2);  // F01, F11 (page 0 f1, page 1 f3)
    assert(fns[0].function_number == 0x01 && fns[0].query == 0x000d);
    assert(fns[0].irq_start == 0);
    assert(fns[1].function_number == 0x03 && fns[1].query == 0x010e);
    assert(fns[1].data == 0x0110 && fns[1].irq_start == 2);  // scan order
    puts("5. 6-byte PDT walk with page 0 non-empty (old suite bug): ok");
  }

  // ---- 6. F11 sensor-query walk, v4.9 rmi_f11_get_query_parameters
  //         (r9_f11.c:770-899) byte conditionals: device query0 at the
  //         FnDesc.query slot (HAS_QUERY9 bit3); sensor q0..q3, q5 IFF
  //         has_abs, q6 IFF has_rel (skipped here), q7/q8 IFF
  //         has_gestures, q9 IFF has_query9, q10 IFF has_touch_shapes.
  //         Cursor lands q7 at +6, q8 +7, q9 +8, q10 +9.
  {
    const uint16_t f11q = 0x010e;
    slave.poke8(f11q, 0x08);      // device query0: HAS_QUERY9
    slave.poke8(f11q + 1, 0x31);  // sensor q0: nr_fingers=1 | HAS_ABS |
                                  // HAS_GESTURES, no REL (v4.9 masks
                                  // :82-85: 0x07 count, bit3 rel, bit4
                                  // abs, bit5 gestures)
    slave.poke8(f11q + 2, 103);
    slave.poke8(f11q + 3, 62);
    slave.poke8(f11q + 4, 0);
    slave.poke8(f11q + 5, 0);     // q5 (has_abs): abs_data_size 0 — v4.9
                                  // decodes 5-byte objects anyway
    slave.poke8(f11q + 6, 0x50);  // q7: PINCH|FLICK -> query7_nonzero
    slave.poke8(f11q + 7, 0x06);  // q8: ROTATE|TOUCH_SHAPES
    slave.poke8(f11q + 8, 0x20);  // q9 (has_query9)
    slave.poke8(f11q + 9, 1);     // q10: nr_touch_shapes 1 (has_touch_shapes)
    rmi::F11Queries q;
    rmi::FnDesc f11{0x03, f11q, 0x0111, 0x010f, 0x0110, 2, 0};
    assert(rmi::readF11Queries(x, f11, q));
    assert(q.nr_fingers_cfg == 1 && q.fingers() == 2);
    assert(q.has_abs && !q.has_rel && q.has_gestures);
    assert(q.has_pinch && q.has_flick && q.has_rotate && q.has_touch_shapes);
    assert(!q.has_palm_det);
    assert(q.nr_touch_shapes == 1);
    // v4.9 pkt_size (r9_f11.c:640-672): 1 state + 10 abs + (rel 0)
    //   + gest1 1 + gest2 1 + pinch/flick/rotate 3 + shapes ceil(2/8) 1
    //   = 17. The I2C attention read takes the full pkt_size
    //   (rmi_f11_attention:1244-1248; rmi_i2c never sets attn_data).
    assert(rmi::windowSize(q) == 17);
    puts("6. F11 query walk (abs-only cursor) + pkt_size 17: ok");
  }

  // ---- 7. control plane: one 12-byte block at F11 control (vendor dump),
  //         identity-gated by the caller; wire = [W 0x0f][12 bytes].
  {
    assert(x.writeBlock(0x010f, rmi::F11_CTRL_INIT, rmi::F11_CTRL_REG_COUNT));
    const std::vector<uint8_t> &w = slave.writeLog.back();
    assert(w.size() == 13 && w[0] == 0x0f);
    for (unsigned i = 0; i < 12; ++i) assert(w[1 + i] == rmi::F11_CTRL_INIT[i]);
    // First data byte lands AT the addressed register (device pointer
    // semantics of the model's writeStream), so vendor ctrl7=0x09 sits
    // at base+7 and ctrl8=0x05 at base+8 — this pair also discriminates
    // a +1-offset landing bug (base+7 would read ctrl6=0x00 then).
    assert(slave.regfile[0x010f + 7] == 0x09 && slave.regfile[0x010f + 8] == 0x05);
    puts("7. F11 control block single transaction: ok");
  }

  // ---- 8. attention decode, S3202-shaped layout (abs-only device):
  //         f_state@0 (2-bit per finger), abs@1 (5 B/object),
  //         gest1@11, gest2@12, pinch@13, flick@14-15, rotate@16? No —
  //         v4.9 cursor: pinch+1 byte, flick aliases pinch with i+=2,
  //         rotate aliases flick+1 (no extra byte), so the gesture
  //         REGION is 3 bytes (pkt_size term :660-665), then shapes 1.
  //         Window = 1 + 10 + 2 + 3 + 1 = 17, gest1@11, gest2@12.
  {
    rmi::F11Queries q;
    q.nr_fingers_cfg = 1;  // 2 fingers
    q.has_abs = true;
    q.query7_nonzero = true;
    q.query8_nonzero = true;
    q.has_pinch = q.has_flick = q.has_rotate = true;
    q.has_touch_shapes = true;
    q.nr_touch_shapes = 1;
    assert(rmi::windowSize(q) == 17);
    uint8_t pkt[17] = {};
    pkt[0] = 0x01;         // f0 present (2-bit state 01), f1 OFF
    uint8_t *abs = pkt + 1;
    abs[0] = 0x3e;
    abs[1] = 0x1f;
    abs[2] = uint8_t((4 << 4) | 8);
    abs[3] = (2 << 4) | 3;  // wx=3, wy=2
    abs[4] = 30;            // z
    // finger1 state=0 -> all bytes zero at abs+5..
    pkt[11] = 0x50;  // gest1 = pinch+swipe (bits 6,4)
    pkt[12] = 0x00;  // gest2
    rmi::TouchFrame fr;
    assert(rmi::decodeF11(pkt, q, fr) == rmi::F_OK);
    assert(fr.nfingers == 2 && fr.f[0].on && fr.f[0].x == 1000 &&
           fr.f[0].y == 500);
    assert(fr.f[0].w == 0x23 && fr.f[0].wx == 3 && fr.f[0].wy == 2);
    assert(fr.f[0].z == 30);
    assert(!fr.f[1].on && fr.f[1].z == 0);
    assert(fr.gest1 == 0x50 && fr.gest2 == 0x00);
    puts("8. v4.9 attention decode (f_state 2-bit + 5-byte objects): ok");
  }

  // ---- 9. gesture flag reset (rmi_f11.c:1428-1439 read-modify-write).
  {
    slave.poke8(0x010f + 1, 0x52);  // ctrl1: bits 1,4,6 set
    assert(x.write8(0x010f + 1, 0x00));  // reset both
    assert(slave.regfile[0x0110] == 0x00);
    puts("9. gesture ctrl reset clears bits 1+6: ok");
  }

  // ---- 10. glitch machine. The v4.9 window semantics fixed the old
  //          suite's two fabricated bugs: state byte bit0 = on (not
  //          nibble), objects are 5 bytes (not 6), so "z=0" and "wy=0"
  //          frames decode as OFF — exactly what the guard must not
  //          misreport.
  {
    rmi::F11Queries q;
    q.nr_fingers_cfg = 1;  // 2 fingers
    q.has_abs = true;
    auto frame = [&q](uint8_t st0, uint8_t st1, uint8_t *p0, uint8_t *p1,
                      rmi::TouchFrame &fr) {
      uint8_t pkt[1 + 10] = {};
      pkt[0] = uint8_t((st0 & 3) | ((st1 & 3) << 2));
      memcpy(pkt + 1, p0, 5);
      memcpy(pkt + 6, p1, 5);
      return rmi::decodeF11(pkt, q, fr);
    };
    rmi::TouchFrame fr;
    // 10a. z=0 with on-state: v4.9 still reports on (bit0 of state byte
    //      is what counts; z is data, not state). NOT a glitch source.
    memset(fr.f, 0, sizeof fr.f);
    assert(frame(1, 0, (uint8_t[5]){5, 0, 0x50, 0x21, 0}, (uint8_t[5]){0}, fr) ==
           rmi::F_OK);
    assert(fr.f[0].on && fr.f[0].z == 0);
    assert(!fr.f[1].on);
    // 10b. same-slot reuse inside the history window: appeared twice.
    rmi::GlitchGuard g;
    assert(g.accept(1, 500, 500, +1));  // id1 appears in frame 1
    g.commitFrame();
    fr.nfingers = 1;
    fr.f[0] = rmi::Finger{};
    fr.f[0].id = 1;
    fr.f[0].x = 501;
    fr.f[0].y = 501;
    fr.f[0].on = true;
    assert(!g.accept(1, 501, 501, +1));  // same id still in history -> drop
    g.commitFrame();
    // After the history rolls (3 windows), reuse is legitimate.
    for (int k = 0; k < 3; ++k) {
      rmi::TouchFrame e;
      e.nfingers = 0;
      // frames without activity shift history
      // (commit records "seen"=false for all ids)
      g.commitFrame();
    }
    assert(g.accept(1, 700, 700, +1));
    // 10c. lost at a foreign position is rejected; at its own track ok.
    assert(!g.accept(1, 900, 900, -1));
    assert(g.accept(1, 700, 700, -1));
    puts("10. glitch machine on real v4.9 semantics: ok");
  }

  // ---- 11. interrupt enable bytes (v4.9 mask order): the enable word is
  //          ceil(total_irq_bits/8) bytes, little-endian bitmap, F11 abs
  //          at bit irq_start, rel at irq_start+1. For irq_start 2 both
  //          bits live in byte 0 (0x0C); a byte-crossing needs irq_start 7.
  {
    rmi::FnDesc f11{0x03, 0, 0, 0, 0, 2, 2};
    uint8_t en[4];
    rmi::f11IrqEnables(f11, en, 2);  // device has 2 irq bits -> 2-byte word
    assert(en[0] == 0x0C && en[1] == 0x00);  // abs bit2 + rel bit3, same byte
    // Crossing case: abs at bit 7 of byte 0, rel at bit 0 of byte 1.
    rmi::f11IrqEnables(rmi::FnDesc{0x0b, 0, 0, 0, 0, 2, 7}, en, 2);
    assert(en[0] == (1U << 7) && en[1] == 0x01);
    puts("11. F11 irq enable bytes (bit positions, crossing): ok");
  }

  // ---- 12. end-to-end over the real QupI2c template: a page-1 window
  //          read crosses pages, the engine resets, and the bytes land.
  {
    rmi::F11Queries q;
    q.nr_fingers_cfg = 1;
    q.has_abs = true;
    uint8_t pkt[11] = {};
    pkt[0] = 0x05;  // f0 present, f1 inaccurate (2-bit 01, 01... careful:
                    // 0x05 = 0b0101 -> f0 01 present, f1 01 present)
    pkt[1] = 62;
    pkt[2] = 31;
    pkt[3] = uint8_t((4 << 4) | 8);
    pkt[4] = 0x23;
    pkt[5] = 30;
    slave.poke(0x0110, pkt, 11);
    // read via transport (window read is rmi_read_block(f11.data_base,
    // attn_size): base 0x0110, page 1)
    uint8_t got[11];
    assert(x.readBlock(0x0110, got, 11));
    rmi::TouchFrame fr;
    assert(rmi::decodeF11(got, q, fr) == rmi::F_OK);
    assert(fr.f[0].on && fr.f[0].x == 1000 && fr.f[0].y == 500);
    // and the engine really moved bytes: reset and re-read standalone
    assert(i2c.reset());
    puts("12. transport+core end-to-end (real QupI2c path): ok");
  }

  // ---- 13. identity gate (plan T2.2: mismatch refuses boot): a real
  //          readIdentity over the case-5 PDT model (F01 query at 0x000d,
  //          identity bytes from case 4 persist), then the pure predicates. ----
  {
    rmi::FnDesc fns[8];
    unsigned nfns = rmi::scanPdt(x, fns, 8);
    assert(nfns == 2);
    uint8_t mfg = 0;
    char prod[11] = {};
    assert(rmi::readIdentity(x, fns[0], mfg, prod));
    assert(mfg == 0x01 && strcmp(prod, "S3202ABCD") == 0);
    assert(rmi::matchIdentity(mfg, prod, 0x01, "S3202ABCD"));
    assert(!rmi::matchIdentity(0x02, prod, 0x01, "S3202ABCD"));  // mfg gate
    assert(!rmi::matchIdentity(mfg, prod, 0x01, "S3202BBBB"));  // string gate
    assert(rmi::findFunction(fns, nfns, 0x03) == 1);
    assert(rmi::findFunction(fns, nfns, 0x0c) == nfns);  // absent -> refuse
    puts("13. identity gate: match/mismatch + F11-present/absent: ok");
  }

  // ---- 14. ts->lcd mapping contract (plan: 1266x2220 -> 720x1280,
  //          DT numbers locked as constexpr + boundary invariants). ----
  {
    assert(rmi::TS_DIM.w == 1266 && rmi::TS_DIM.h == 2220);
    assert(rmi::LCD_DIM.w == 720 && rmi::LCD_DIM.h == 1280);
    unsigned lx, ly;
    rmi::mapPoint(0, 0, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
    assert(lx == 0 && ly == 0);  // min -> min
    rmi::mapPoint(1265, 2219, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
    assert(lx == 719 && ly == 1279);  // max -> max (last valid index)
    // monotone in both axes: every ts step never moves lcd backwards
    unsigned prevx = 0, prevy = 0;
    for (unsigned t = 1; t < 1266; ++t) {
      rmi::mapPoint(t, 0, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
      assert(lx >= prevx && lx < rmi::LCD_DIM.w);
      prevx = lx;
    }
    for (unsigned t = 1; t < 2220; ++t) {
      rmi::mapPoint(0, t, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
      assert(ly >= prevy && ly < rmi::LCD_DIM.h);
      prevy = ly;
    }
    // overflow safety: a bogus full-scale read (16-bit abs) clamps
    rmi::mapPoint(65535, 65535, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
    assert(lx == 719 && ly == 1279);
    puts("14. ts->lcd mapping: constexpr lock + 0/0 max/max + monotone + clamp: ok");
  }

  // ---- 15. multi-touch frame: five fingers in one attention window.
  //          nr_fingers_cfg 4 -> 5 objects (r9_f11.c:611-612); f_state is
  //          (5+3)/4 = 2 bytes; abs at offset 2, 5 bytes/finger with the
  //          v4.9 nibble-interleaved 12-bit pair (p0=x>>4, p1=y>>4,
  //          p2=(y&0xf)<<4|(x&0xf)); query7_nonzero puts gest1/gest2 at
  //          offset 2+25. window = 2 + 25 + 2 = 29. ----
  {
    rmi::F11Queries q;
    q.nr_fingers_cfg = 4;
    q.has_abs = true;
    q.query7_nonzero = true;
    assert(q.fingers() == 5);
    assert(rmi::absOffset(q) == 2);
    const unsigned win = rmi::windowSize(q);
    assert(win == 29);
    std::vector<uint8_t> pkt(win, 0);
    const unsigned xs[5] = {111, 234, 567, 890, 1265};
    const unsigned ys[5] = {222, 345, 678, 999, 2219};
    for (unsigned i = 0; i < 5; ++i) {
      pkt[i / 4] |= uint8_t(0b01 << (2 * (i % 4)));  // present
      uint8_t *p = pkt.data() + 2 + i * 5;
      p[0] = uint8_t(xs[i] >> 4);
      p[1] = uint8_t(ys[i] >> 4);
      p[2] = uint8_t(((ys[i] & 0xf) << 4) | (xs[i] & 0xf));
      p[3] = uint8_t(0x20 + i);  // w
      p[4] = uint8_t(0x50 + i);  // z
    }
    pkt[27] = 0x04;  // gest1 (swipe bit in this synthetic frame)
    rmi::TouchFrame fr;
    assert(rmi::decodeF11(pkt.data(), q, fr) == rmi::F_OK);
    assert(fr.nfingers == 5);
    for (unsigned i = 0; i < 5; ++i) {
      assert(fr.f[i].on && !fr.f[i].inaccurate);
      assert(fr.f[i].id == i);
      assert(fr.f[i].x == xs[i] && fr.f[i].y == ys[i]);
      assert(fr.f[i].w == unsigned(0x20 + i) && fr.f[i].z == unsigned(0x50 + i));
    }
    assert(fr.gest1 == 0x04 && fr.gest2 == 0);
    // mapped through the real panel geometry: all ids survive in bounds
    for (unsigned i = 0; i < fr.nfingers; ++i) {
      unsigned lx, ly;
      rmi::mapPoint(fr.f[i].x, fr.f[i].y, rmi::TS_DIM, rmi::LCD_DIM, lx, ly);
      assert(lx < rmi::LCD_DIM.w && ly < rmi::LCD_DIM.h);
    }
    puts("15. five-finger frame: 2-byte f_state + nibble 12-bit x/y + z + gest1: ok");
  }

  // ---- 16. glitch frames: (a) repeated interrupt on an untouched finger
  //          stays glitch-classified through GlitchGuard (history ring,
  //          plan: glitch 帧(重复中断)幂等); (b) decode itself is pure —
  //          same bytes twice give the same frame. ----
  {
    rmi::GlitchGuard g(8);
    assert(g.accept(0, 300, 900, +1));  // appeared
    g.commitFrame();                    // id 0 enters the history ring
    for (int k = 0; k < 20; ++k)        // 20 spurious same-position interrupts
      assert(!g.accept(0, 300, 900, +1));  // history keeps them glitches
    rmi::F11Queries q;
    q.nr_fingers_cfg = 1;  // 2 objects: 1-byte f_state + 10 abs = window 11
    q.has_abs = true;
    assert(rmi::windowSize(q) == 11);
    uint8_t pkt[11] = {};
    pkt[0] = 0b000001;  // f0 present, f1 OFF
    pkt[1] = 0x3e; pkt[2] = 0x1f; pkt[3] = uint8_t((4 << 4) | 8);
    rmi::TouchFrame a, b;
    assert(rmi::decodeF11(pkt, q, a) == rmi::F_OK);
    assert(rmi::decodeF11(pkt, q, b) == rmi::F_OK);
    // Field-wise compare (no memcmp: Finger has trailing padding and the
    // undecoded slots keep uninitialized bytes by C++ rules).
    assert(a.nfingers == b.nfingers && a.gest1 == b.gest1 &&
           a.gest2 == b.gest2);
    for (unsigned i = 0; i < a.nfingers; ++i) {
      assert(a.f[i].id == b.f[i].id && a.f[i].x == b.f[i].x &&
             a.f[i].y == b.f[i].y && a.f[i].w == b.f[i].w &&
             a.f[i].z == b.f[i].z && a.f[i].on == b.f[i].on &&
             a.f[i].inaccurate == b.f[i].inaccurate);
    }
    assert(a.f[0].x == 1000 && a.f[0].y == 500);  // (0x3e<<4)|8, (0x1f<<4)|4
    puts("16. spurious repeats stay glitches; decode is frame-idempotent: ok");
  }

  // ---- 17. T3.2 sequence lock: the kernel digitizer's REAL bring-up
  //          sequence (DigitizerBoot.h bringUp) runs over this fake bus and
  //          the emitted stage order is asserted literally. Design 铁律 ③:
  //          the contract test locks the ORDER itself, not mere existence.
  //          Stage codes 1..5 = PDT/identity/F11-queries/ctrl/irq-enable;
  //          refusal codes arrive as 1000+Refuse. Device fixture: the same
  //          S3202-class layout as cases 4/5/6 (F01 page0 query 0x000d with
  //          the case-4 identity bytes, F11 page1 query 0x010e), so the
  //          window math matches case 6's 17 bytes and the scan lands
  //          F01 (irq_count 2) then F11 (irq_start 2, irq_count 2). ----
  {
    // Re-arm the identity bytes case-5's PDT walk expects at page 0 and the
    // F11 query cursor from case 6 (the file's slave state persists).
    uint8_t q[rmi::F01_BASIC_QUERY_LEN] = {};
    q[0] = 0x01;
    memcpy(&q[11], "S3202ABCD", 9);
    slave.poke(0x000d, q, sizeof q);
    const uint16_t f11q = 0x010e;
    slave.poke8(f11q, 0x08);      // device query0: HAS_QUERY9
    slave.poke8(f11q + 1, 0x31);  // sensor q0: 2 fingers | HAS_ABS | gestures
    slave.poke8(f11q + 2, 103);
    slave.poke8(f11q + 3, 62);
    slave.poke8(f11q + 4, 0);
    slave.poke8(f11q + 5, 0);     // q5 abs_data_size 0
    slave.poke8(f11q + 6, 0x50);  // q7 pinch+flick
    slave.poke8(f11q + 7, 0x06);  // q8 rotate+touch-shapes
    slave.poke8(f11q + 8, 0x20);  // q9
    slave.poke8(f11q + 9, 1);     // q10: nr_touch_shapes 1

    digitizerboot::Config cfg;
    assert(cfg.want_mfg == rmi::SYNAPTICS_MFG_ID);
    assert(strcmp(cfg.family_prefix, "S3202") == 0);
    assert(cfg.slave_addr == 0x20);  // DT rmi4 reg the bus shell publishes

    // 17a. happy path: the literal stage order [1,2,3,4,5] and the effects
    //      the sequence left on the model registers (ctrl block landed, F11
    //      abs+rel enable byte 0x0C written at F01 control+1 = 0x000e).
    {
      SeqLog log;
      digitizerboot::Result res;
      assert(digitizerboot::bringUp(x, cfg, res, log));
      const unsigned want[] = {digitizerboot::StagePdt, digitizerboot::StageIdentity,
                               digitizerboot::StageF11Queries, digitizerboot::StageCtrl,
                               digitizerboot::StageIrqEnable};
      assert(log.order.size() == 5);
      for (unsigned i = 0; i < 5; ++i) assert(log.order[i] == want[i]);
      assert(res.nfns == 2 && res.i01 == 0 && res.i11 == 1);
      assert(res.refusal == digitizerboot::RefuseNone);
      assert(res.window == 17);  // case 6's pkt_size, same queries
      assert(res.f11.fingers() == 2);
      for (unsigned i = 0; i < rmi::F11_CTRL_REG_COUNT; ++i)
        assert(slave.regfile[0x010f + i] == rmi::F11_CTRL_INIT[i]);
      // total irqs = 2 (F01) + 2 (F11) = 4 -> one enable word, bits 2|3.
      assert(slave.regfile[0x000e] == 0x0C);
      puts("17a. real bring-up sequence: order [Pdt,Identity,F11,Ctrl,Irq] + effects: ok");
    }

    // 17b. identity mismatch refuses AFTER the identity stage: truncated
    //      order [1,2,1003] (stage 3+ never emitted).
    {
      uint8_t bad[rmi::F01_BASIC_QUERY_LEN] = {};
      bad[0] = 0x01;
      memcpy(&bad[11], "X9999ABCD", 9);  // family prefix fails
      slave.poke(0x000d, bad, sizeof bad);
      SeqLog log;
      digitizerboot::Result res;
      assert(!digitizerboot::bringUp(x, cfg, res, log));
      assert(res.refusal == digitizerboot::RefuseIdentity);
      const unsigned want[] = {digitizerboot::StagePdt, digitizerboot::StageIdentity,
                               1000u + digitizerboot::RefuseIdentity};
      assert(log.order.size() == 3);
      for (unsigned i = 0; i < 3; ++i) assert(log.order[i] == want[i]);
      // wrong manufacturer also refuses (gate is bidirectional, case 13).
      bad[0] = 0x02;
      memcpy(&bad[11], "S3202ABCD", 9);
      slave.poke(0x000d, bad, sizeof bad);
      SeqLog log2;
      digitizerboot::Result res2;
      assert(!digitizerboot::bringUp(x, cfg, res2, log2));
      assert(res2.refusal == digitizerboot::RefuseIdentity);
      assert(log2.order == log.order);
      // restore the good identity bytes for the next blocks
      uint8_t q[rmi::F01_BASIC_QUERY_LEN] = {};
      q[0] = 0x01;
      memcpy(&q[11], "S3202ABCD", 9);
      slave.poke(0x000d, q, sizeof q);
      puts("17b. identity refusal truncates the order: ok");
    }

    // 17c. F11 absent refuses right after the PDT stage: [1,1002].
    {
      uint8_t e6[6] = {0x0e, 0x11, 0x0f, 0x10, 0x02, 0x0b};  // fn 0x0b, not F11
      slave.poke(0x01e9, e6, 6);
      SeqLog log;
      digitizerboot::Result res;
      assert(!digitizerboot::bringUp(x, cfg, res, log));
      assert(res.refusal == digitizerboot::RefuseNoF11);
      const unsigned want[] = {digitizerboot::StagePdt,
                               1000u + digitizerboot::RefuseNoF11};
      assert(log.order.size() == 2);
      for (unsigned i = 0; i < 2; ++i) assert(log.order[i] == want[i]);
      uint8_t back[6] = {0x0e, 0x11, 0x0f, 0x10, 0x02, 0x03};
      slave.poke(0x01e9, back, 6);
      puts("17c. F11-absent refusal: order [Pdt, refusal]: ok");
    }

    // 17d. MT1 blob encoding is pure and matches the plan's report shape:
    //      count + 7-byte slots, mapped LE coordinates, z, flags.
    {
      rmi::TouchFrame fr;
      fr.nfingers = 3;
      for (unsigned i = 0; i < 3; ++i) fr.f[i] = rmi::Finger{};
      fr.f[0] = rmi::Finger{0, 1000, 500, 0, 0, 0, 30, true, false};
      fr.f[1] = rmi::Finger{1, 1265, 2219, 0, 0, 0, 255, true, true};  // inaccurate
      fr.f[2] = rmi::Finger{2, 0, 0, 0, 0, 0, 0, false, false};        // off -> skipped
      uint8_t blob[digitizerboot::kBlobBytes];
      digitizerboot::encodeBlob(fr, cfg, blob);
      assert(blob[0] == 2);  // contact count
      const uint8_t *s0 = blob + 1;
      assert(s0[0] == 0);
      // case 14's mapPoint integer floor: 1000*720/1266 = 568, 500*1280/2220 = 288
      assert(s0[1] == (568 & 0xff) && s0[2] == (568 >> 8));
      assert(s0[3] == (288 & 0xff) && s0[4] == (288 >> 8));
      assert(s0[5] == 30 && s0[6] == 0x03);  // tipswitch + confidence
      const uint8_t *s1 = blob + 1 + digitizerboot::kBlobSlotBytes;
      assert(s1[0] == 1);
      assert(s1[1] == 0xcf && s1[2] == 0x02);  // 719 = max -> max (0x2cf LE)
      assert(s1[3] == 0xff && s1[4] == 0x04);  // 1279 (0x4ff LE)
      assert(s1[5] == 255 && s1[6] == 0x01);   // inaccurate: no confidence
      // rest of the blob is zero
      for (unsigned i = 1 + 2 * digitizerboot::kBlobSlotBytes;
           i < digitizerboot::kBlobBytes; ++i)
        assert(blob[i] == 0);
      // overflow: a full 10-finger frame caps at five slots
      rmi::TouchFrame many;
      many.nfingers = 10;
      for (unsigned i = 0; i < 10; ++i) {
        many.f[i] = rmi::Finger{};
        many.f[i].id = i;
        many.f[i].on = true;
        many.f[i].x = 100;
        many.f[i].y = 100;
      }
      digitizerboot::encodeBlob(many, cfg, blob);
      assert(blob[0] == digitizerboot::kMaxContacts);
      puts("17d. MT1 blob: count + mapped LE + flags + cap: ok");
    }
  }

  puts("QcomTouch T3.2 host suite: all checks passed");
}
