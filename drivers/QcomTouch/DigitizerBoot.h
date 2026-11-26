// SPDX-License-Identifier: BSD-2-Clause-Patent
// DigitizerBoot.h — the ordered RMI4/S3202 bring-up sequence shared by the
// kernel digitizer (drivers/QcomTouch/NativeHidDigitizer.cpp) and the host
// contract suite (Test/touch_host.cpp case 17). T2.1/RmiCore.h supplies the
// decoding; this header supplies the SEQUENCE: PDT scan -> F01 identity gate
// -> F11 query walk -> control block -> interrupt enables. Templated on the
// transport (anything with rmi::RmiXport-shaped readBlock/writeBlock through
// an X object) and on a stage logger, so the host test records the literal
// call order of the exact code the kernel runs (设计规范铁律: 锁顺序本身).
//
// Ground rules, all inherited from RmiCore.h's v4.9 provenance:
//   - identity gate: manufacturer must equal cfg.want_mfg and the 10-byte
//     product string must start with cfg.family_prefix ("家族字段" per plan
//     Risks table; full product bytes are kept in res.product as evidence).
//   - F01 or F11 missing after the PDT walk refuses boot (plan T2.2).
//   - control block is ONE 12-byte write at f11.control (v4.9
//     f11_write_control_regs shape, F11_CTRL_INIT candidate snapshot —
//     UNVERIFIED PROVENANCE until the T0 device re-capture, same caveat as
//     RmiCore.h).
//   - interrupt enables: little-endian bitmap at f01.control+1 sized by the
//     total irq bits the PDT walk accumulated (v4.9 rmi_driver.c:147-149,
//     363 — enable words at F01 control_base_addr+1, f11IrqEnables bits).
//   - attention intake stays OUTSIDE this sequence: after boot the caller
//     polls (readBlock at f11.data of res.window bytes -> rmi::decodeF11 ->
//     encodeBlob below). No IRQ registration in T3.2; T5 owns that.
#ifndef QCOMTOUCH_DIGITIZERBOOT_H
#define QCOMTOUCH_DIGITIZERBOOT_H

#include <stdint.h>
#include <string.h>

#include "RmiCore.h"

namespace digitizerboot {

// Stage codes the ordered log carries. The host test asserts the literal
// sequence [StagePdt, StageIdentity, StageF11Queries, StageCtrl,
// StageIrqEnable] on the happy path and the truncated prefixes on refusal.
enum Stage : unsigned {
  StagePdt = 1,
  StageIdentity = 2,
  StageF11Queries = 3,
  StageCtrl = 4,
  StageIrqEnable = 5,
};

enum Refusal : unsigned {
  RefuseNone = 0,
  RefuseNoF01 = 1,       // PDT walk never found function 0x01
  RefuseNoF11 = 2,       // PDT walk never found function 0x03 (plan T2.2)
  RefuseIdentity = 3,    // manufacturer or family prefix mismatch
  RefuseNoAbs = 4,       // F11 without abs reporting cannot drive a digitizer
  RefuseWindow = 5,      // attention window arithmetic exceeded the model
  RefuseTransport = 6,   // a bus transaction failed (error code kept separately)
};

static constexpr unsigned MAX_FNS = 8;

struct Config {
  uint8_t want_mfg = rmi::SYNAPTICS_MFG_ID;
  char family_prefix[8] = "S3202";  // prefix of the 10-byte F01 product id
  rmi::Dim ts = rmi::TS_DIM;
  rmi::Dim lcd = rmi::LCD_DIM;
  uint32_t slave_addr = 0x20;       // DT reg of rmi4 (ADT writes 0x20)
};

struct Result {
  unsigned nfns = 0;
  rmi::FnDesc fns[MAX_FNS] = {};
  unsigned i01 = 0, i11 = 0;        // indices into fns once boot succeeded
  rmi::F11Queries f11 = {};
  uint8_t manufacturer = 0;
  char product[rmi::PRODUCT_ID_LEN + 1] = {};
  uint8_t window = 0;              // attention window size (bytes)
  unsigned refusal = RefuseNone;
};

// prefixMatch: first len bytes of product equal prefix (len <= PRODUCT_ID_LEN).
inline bool prefixMatch(const char *product, const char *prefix, unsigned len) {
  if (len == 0 || len > rmi::PRODUCT_ID_LEN) return false;
  for (unsigned i = 0; i < len; ++i)
    if (product[i] != prefix[i]) return false;
  return true;
}

// bringUp runs the sequence; LOG must expose stage(unsigned) and
// refusal(unsigned). Returns true only after StageIrqEnable completed.
// X must expose the rmi::RmiXport surface (readBlock/writeBlock/write8).
template <class X, class LOG>
inline bool bringUp(X &x, const Config &cfg, Result &res, LOG &log) {
  res.nfns = rmi::scanPdt(x, res.fns, MAX_FNS);
  log.stage(StagePdt);
  res.i01 = rmi::findFunction(res.fns, res.nfns, 0x01);
  res.i11 = rmi::findFunction(res.fns, res.nfns, 0x03);
  if (res.i01 == res.nfns) {
    res.refusal = RefuseNoF01;
    log.refusal(res.refusal);
    return false;
  }
  if (res.i11 == res.nfns) {  // F11 absent refuses boot (plan T2.2)
    res.refusal = RefuseNoF11;
    log.refusal(res.refusal);
    return false;
  }
  if (!rmi::readIdentity(x, res.fns[res.i01], res.manufacturer, res.product)) {
    res.refusal = RefuseTransport;
    log.refusal(res.refusal);
    return false;
  }
  log.stage(StageIdentity);
  unsigned plen = (unsigned)strlen(cfg.family_prefix);
  if (res.manufacturer != cfg.want_mfg ||
      !prefixMatch(res.product, cfg.family_prefix, plen)) {
    res.refusal = RefuseIdentity;
    log.refusal(res.refusal);
    return false;
  }
  const rmi::FnDesc &f11 = res.fns[res.i11];
  if (!rmi::readF11Queries(x, f11, res.f11)) {
    res.refusal = RefuseTransport;
    log.refusal(res.refusal);
    return false;
  }
  log.stage(StageF11Queries);
  if (!res.f11.has_abs) {  // a digitizer without absolute positions is useless
    res.refusal = RefuseNoAbs;
    log.refusal(res.refusal);
    return false;
  }
  unsigned win = rmi::windowSize(res.f11);
  if (win == 0 || win > 256) {  // Msg.len cap of the transport (256 read max)
    res.refusal = RefuseWindow;
    log.refusal(res.refusal);
    return false;
  }
  res.window = uint8_t(win);
  if (!x.writeBlock(f11.control, rmi::F11_CTRL_INIT, rmi::F11_CTRL_REG_COUNT)) {
    res.refusal = RefuseTransport;
    log.refusal(res.refusal);
    return false;
  }
  log.stage(StageCtrl);
  // Interrupt enables: bits for F11 abs/rel at the F01 enable register bank
  // (control_base+1). Width = total irq bits the scan accumulated.
  unsigned total_irqs = 0;
  for (unsigned i = 0; i < res.nfns; ++i)
    total_irqs += res.fns[i].irq_count;
  unsigned words = (total_irqs + 7) / 8;
  if (words == 0) words = 1;
  if (words > 8) {  // model cap; v4.9 sizes dynamically, we refuse instead
    res.refusal = RefuseWindow;
    log.refusal(res.refusal);
    return false;
  }
  uint8_t en[8] = {};
  rmi::f11IrqEnables(f11, en, words);
  const rmi::FnDesc &f01 = res.fns[res.i01];
  for (unsigned w = 0; w < words; ++w) {
    if (!x.write8(uint16_t(f01.control + 1 + w), en[w])) {
      res.refusal = RefuseTransport;
      log.refusal(res.refusal);
      return false;
    }
  }
  log.stage(StageIrqEnable);
  res.refusal = RefuseNone;
  return true;
}

// ---- MT1-style report blob (pure; the kernel packs it under its IOLock and
// the host test locks the same encoding) ----
// Layout: [0] contact count; then kMaxContacts slots of 7 bytes each:
//   +0 transducer index | +1..2 x LE (lcd logical) | +3..4 y LE
//   | +5 z (pressure proxy) | +6 bit0 tipswitch, bit1 confidence.
// Contacts beyond the count stay zeroed. 1-5 contacts per plan T2.2; the
// tenth-capable decode is narrowed to five at the blob edge (MT1 convention).
static constexpr unsigned kMaxContacts = 5;
static constexpr unsigned kBlobSlotBytes = 7;
static constexpr unsigned kBlobBytes = 1 + kMaxContacts * kBlobSlotBytes;

inline void encodeBlob(const rmi::TouchFrame &fr, const digitizerboot::Config &cfg,
                       uint8_t *out) {
  memset(out, 0, kBlobBytes);
  unsigned n = fr.nfingers;
  if (n > kMaxContacts) n = kMaxContacts;
  unsigned count = 0;
  for (unsigned i = 0; i < n; ++i) {
    const rmi::Finger &fg = fr.f[i];
    if (!fg.on) continue;
    unsigned lx, ly;
    rmi::mapPoint(fg.x, fg.y, cfg.ts, cfg.lcd, lx, ly);
    uint8_t *slot = out + 1 + count * kBlobSlotBytes;
    slot[0] = uint8_t(fg.id);
    slot[1] = uint8_t(lx & 0xff);
    slot[2] = uint8_t(lx >> 8);
    slot[3] = uint8_t(ly & 0xff);
    slot[4] = uint8_t(ly >> 8);
    slot[5] = uint8_t(fg.z > 0xff ? 0xff : fg.z);
    slot[6] = 0x01;                        // tipswitch
    if (!fg.inaccurate) slot[6] |= 0x02;   // confidence
    ++count;
  }
  out[0] = uint8_t(count);
}

}  // namespace digitizerboot

#endif  // QCOMTOUCH_DIGITIZERBOOT_H
