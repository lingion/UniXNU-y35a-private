// SPDX-License-Identifier: BSD-2-Clause
// RAM-only RMI4/S3202 identity probe for the measured LK2nd Y35A handoff
// (plan docs/superpowers/plans/2026-11-05-y35a-touch-driver.md T0.2).
//
// What this settles, and what it deliberately refuses to guess (each
// refusal is a measured fact, cite before changing):
//  - lk2nd platform/msm8916/acpuclock.c:485-515 (read 2026-11-09 from
//    /work/lk2nd-y35a-codex inside the build container): its
//    clock_config_blsp_i2c ASSERTS for any QUP other than 2 and 4, so
//    the touch bus BLSP1/QUP5 (i2c@78b9000) gates were demonstrably
//    never configured by LK. An ACK here cannot be assumed; NACK/timeout
//    is a legitimate verdict, not a probe bug.
//  - The DT clock cells (clocks=<0x42 0x8caa5b4f 0x42 0xacae5604>,
//    evidence dtb10-stock.dts:6843) are Linux clock NAME hashes, not GCC
//    register indices. This corrected collector therefore reads only the
//    source-pinned target windows: TLMM GPIO12/13/18/19 ctl/io/intr_cfg/
//    intr_status at base + pin*0x1000 + {0,4,8,c}, and GCC+0x6000..0x6024
//    plus GCC+0x45000..0x45008 for the QUP5/BLSP1-AHB controls. The old
//    broad +4 TLMM and GCC+0x800 dumps are not hardware evidence.
//  - Pin identities come from the stock DT verbatim: SDA/SCL = TLMM
//    19/18 (pmx_i2c_5 qcom,pins=<0x3f 0x13 0x3f 0x12>), reset = 12
//    (synaptics,reset-gpio=<0x48 0x0c 0x00>), attn irq = 13
//    (synaptics,irq-gpio=<0x48 0x0d 0x00>, attn_polarity 0).
//  - Reporting follows the 9032a64/baf4604 adjudication AND the
//    candidate convention of
//    docs/coordination/claude-codex-sync/CAPTURE-TRANSPORT-AUDIT-20261109.md:
//    the report lives ABOVE the pram window (PANIC_LOG_DEST, passed in
//    as Y35A_REPORT_BASE by probe_rmi.py, derived from
//    readback_native.py's own literal) so this probe never writes a
//    byte of 0x859e0000..0x859f0000 — pram remnants stay intact for the
//    readback line (defect-1 discipline). The standalone touch probe
//    needs no snapshot dance (no XNU is present to write an EPH header
//    concurrently; the probe spins at wfe and never panics), but it
//    keeps the same report-above-pram address discipline so one memory
//    map serves both lines. The entry stack sits below the pram window
//    (derived: pram_base - 0x1000, grows downward, out of pram).
//    Every dirty line is flushed with dc civac before the wfe spin, so
//    a warm reset preserves the report and the `oem y35a panic`
//    staging (0x859e0000..0x859f1000) uploads it at body offset
//    0x10000. No XNU, no partition writes, no pinctrl or regulator
//    writes, no BAM.
//  - The only hardware WRITE traffic is the QUP5 SE engine's own window
//    (SW_RESET + SE configuration, then one read-only transaction on
//    slave 0x20) through I2cCore, whose dividers (fs 0x16/high 0x17,
//    400 kHz out, 19.2 MHz in) are the dtb10-locked T0.1 constants.
//
// Polling pacing: I2cCore bounds loops by iteration count and calls
// IO::delay() per spin, so delay() must be real time. One tick here is
// 33 CNTVCT counts. The msm8916 arch-timer rate is NOT assumed: the
// probe records cntfrq_el0 plus every transaction timestamp, so the
// real pace (33/cntfrq per spin, and the worst-case bounded totals
// 20000/40000/100000 iterations) is computable from the report itself.

#include <stdint.h>

#include "I2cCore.h"

struct Hardware {
  uintptr_t base;
  uint32_t read32(uint32_t r) const { return *(volatile uint32_t *)(base + r); }
  void write32(uint32_t r, uint32_t v) {
    *(volatile uint32_t *)(base + r) = v;
    asm volatile("dsb sy" ::: "memory");
  }
  void barrier() const { asm volatile("dsb sy" ::: "memory"); }
  void delay() const {
    uint64_t start, now;
    asm volatile("mrs %0,cntvct_el0" : "=r"(start));
    do { asm volatile("mrs %0,cntvct_el0" : "=r"(now)); } while (now - start < 33);
  }
};

static inline uint64_t now64() {
  uint64_t v;
  asm volatile("mrs %0,cntvct_el0" : "=r"(v));
  return v;
}
static inline uint64_t cntfreq() {
  uint64_t v;
  asm volatile("mrs %0,cntfrq_el0" : "=r"(v));
  return v;
}
static uint32_t rawRead(uintptr_t addr) { return *(volatile uint32_t *)addr; }

// ---- report layout (mirrored in probe_rmi.py's manifest) ----
// Standalone-image form per emmc_probe precedent; the +0x10 slot keeps
// the readback tooling's freshness-witness convention (a CNTVCT stamp
// that must differ across captures of the same staged buffer —
// baf4604). Y35A_REPORT_BASE and Y35A_PRAM_BASE are supplied by
// probe_rmi.py, derived from readback_native.py's own literals
// (PANIC_LOG_DEST and STAGE_BASE — the current PRAM declaration). No
// fallback defines on purpose: if the transport convention lands with
// migrated literals, the next build re-stamps itself, and a
// hand-compile without the -D flags fails loudly instead of drifting
// to stale addresses.
//
// The report base is ABOVE the pram window (CAPTURE-TRANSPORT-
// AUDIT-20261109.md candidate geometry, adopted 09:5x): the probe
// writes nothing into pram, so the 64 KiB panic remnants stay intact
// for the readback line (defect-1 discipline). For this standalone
// probe the audit's snapshot/copy-back dance is deliberately NOT
// needed — no XNU is running to consume the EPH header, and the probe
// never resets from within — but the same address discipline is kept
// so one memory map serves both lines. The `oem y35a panic` upload
// (LK fastboot_stage of [STAGE_BASE, 0x11000)) carries this report at
// body offset 0x10000 = report base - LK stage base.
constexpr uint32_t REPORT_BASE = Y35A_REPORT_BASE;
constexpr uint32_t PRAM_BASE = Y35A_PRAM_BASE;
static_assert(REPORT_BASE >= PRAM_BASE + 0x10000,
              "report base must sit at or above the end of pram");
struct Report {
  volatile uint64_t magic;        // 0x00 'Y35ARD01' little-endian
  volatile uint64_t t_boot;       // 0x08 freshness witness: cntvct at start
  volatile uint64_t cntfrq;       // 0x10 CNTVCT rate for interval math
  volatile uint32_t status;       // 0x18 verdict bitmap
  volatile uint32_t err;          // 0x1c qup::Err | (xfer failed) <<24
  volatile uint32_t se_dump[12];  // 0x20 SE window as found, before writes
  volatile uint64_t t_xfer0;      // 0x50 start of identity transaction
  volatile uint64_t t_xfer1;      // 0x58 end of identity transaction
  volatile uint64_t t_end;        // 0x60
  volatile uint32_t clkctl_after; // 0x68 SE_I2C_CLK_CTL after reset()
  volatile uint32_t err2;         // 0x6c F01 follow-on error
  volatile uint8_t page0[8];      // 0x70 RMI4 page 0, offsets 0x00..0x07
  volatile uint8_t f01[21];       // 0x78 page 0 0x0e..0x24 (only after ACK;
                                  //     F01 basic query IF F01 sits at the
                                  //     boot-state default — recorded as raw
                                  //     evidence, never asserted here)
  volatile uint32_t attn_input[4];  // 0x90 GPIO13 input, four samples
  volatile uint32_t attn_status[4]; // 0xa0 GPIO13 interrupt status, four samples
  // 0xb0: ctl/io/intr_cfg/intr_status for GPIO12,13,18,19. The TLMM
  // per-pin window stride is 0x1000; a +4 loop samples only GPIO0.
  volatile uint32_t tlmm_target[16];
  // 0xf0: GCC+0x6000..0x6024 (QUP5 RCG/branch/reset) followed by
  // GCC+0x45000..0x45008 (BLSP1 AHB vote window).
  volatile uint32_t gcc_q5[13];
};
static_assert(sizeof(Report) <= 0x1000,
              "report must fit between the end of pram (0x859f0000) and "
              "the end of the current LK stage extent (+0x11000); growing "
              "it needs the CAPTURE-TRANSPORT-AUDIT lk-stage-size change");

enum : uint32_t {
  S_SE_RESET_FAIL = 1U << 0,  // MASTER_GEN never came up (clock gated?)
  S_PAGE0_ACK = 1U << 1,      // 0x20 answered — bus usable as handed over
  S_PAGE0_NACK = 1U << 2,     // NACK — pins/device not listening
  S_PAGE0_TIMEOUT = 1U << 3,  // engine timeout — consistent with gated clock
  S_F01_ACK = 1U << 4,
  S_DONE = 1U << 31,
};

extern "C" void probe_main() {
  volatile Report *rep = (volatile Report *)REPORT_BASE;
  // Zero with a plain loop: -nostdlib links, no libc calls (emmc_probe
  // precedent).
  volatile uint32_t *zw = (volatile uint32_t *)rep;
  for (unsigned i = 0; i < sizeof(Report) / 4; ++i) zw[i] = 0;
  rep->magic = 0x3130445241353359ULL;  // 'Y35ARD01', little-endian
  uint32_t st = 0;
  rep->t_boot = now64();
  rep->cntfrq = cntfreq();

  Hardware io{0x078b9000};
  QupI2c<Hardware> bus(io);  // I2cCore.h declares the template at global
                             // scope; only the register map is in qup::

  // 1) SE window exactly as handed over — reads only. Named offsets from
  //    the I2cCore map; FIFO windows are deliberately NOT read (a read
  //    consumes an entry).
  static constexpr uint32_t offsets[] = {
      qup::SE_CONFIG,         qup::SE_STATE,          qup::SE_IO_MODE,
      qup::SE_SW_RESET,       qup::SE_OPERATIONAL,    qup::SE_ERROR_FLAGS,
      qup::SE_ERROR_FLAGS_EN, qup::SE_MX_WR_CNT,      qup::SE_MX_INPUT_CNT,
      qup::SE_MX_READ_CNT,    qup::SE_I2C_CLK_CTL,    qup::SE_I2C_STATUS};
  for (unsigned i = 0; i < sizeof(offsets) / sizeof(offsets[0]); ++i)
    rep->se_dump[i] = io.read32(offsets[i]);

  // 2) Exact target register windows. These are reads only; the old broad
  // dumps used the wrong TLMM stride and stopped before the QUP5 GCC gates.
  static constexpr uint32_t pins[] = {12, 13, 18, 19};
  static constexpr uint32_t tlmm_offsets[] = {0x0, 0x4, 0x8, 0xc};
  unsigned tlmm_index = 0;
  for (unsigned p = 0; p < sizeof(pins) / sizeof(pins[0]); ++p)
    for (unsigned r = 0; r < sizeof(tlmm_offsets) / sizeof(tlmm_offsets[0]); ++r)
      rep->tlmm_target[tlmm_index++] =
          rawRead(0x01000000 + pins[p] * 0x1000 + tlmm_offsets[r]);

  static constexpr uint32_t gcc_offsets[] = {
      0x06000, 0x06004, 0x06008, 0x0600c, 0x06010, 0x06014,
      0x06018, 0x0601c, 0x06020, 0x06024, 0x45000, 0x45004, 0x45008};
  for (unsigned i = 0; i < sizeof(gcc_offsets) / sizeof(gcc_offsets[0]); ++i)
    rep->gcc_q5[i] = rawRead(0x01800000 + gcc_offsets[i]);

  // attn line, 4 samples (~tens of ms apart at the recorded cntfrq):
  // if anything toggles the input buffer we see it; polarity stays a
  // T0.3 offline interpretation.
  for (unsigned i = 0; i < 4; ++i) {
    rep->attn_input[i] = rawRead(0x01000000 + 13 * 0x1000 + 0x4);
    rep->attn_status[i] = rawRead(0x01000000 + 13 * 0x1000 + 0xc);
    io.delay();
  }

  // 3) One read-only identity transaction on the SE engine in whatever
  //    state the handoff left it. reset() touches only the SE window.
  //    The divider is the T0.1 wire contract: setClock(19.2 MHz, 400 kHz)
  //    computes fs_div 21/hs_div 3 into SE_I2C_CLK_CTL on the next RUN
  //    transition (I2cCore.h; DT clk-freq-in/out, dtb10-stock.dts:6844).
  bus.setClock(19200000, 400000);
  bool ready = bus.reset();
  rep->clkctl_after = io.read32(qup::SE_I2C_CLK_CTL);

  uint8_t w = 0x00;  // page 0 base — no page-select write needed
  uint8_t rd[8] = {};
  qup::Msg msgs[2] = {{0x20, false, 1, &w}, {0x20, true, 8, rd}};
  rep->t_xfer0 = now64();
  bool ok = ready && bus.xfer(msgs, 2);
  rep->t_xfer1 = now64();
  for (unsigned i = 0; i < 8; ++i) rep->page0[i] = rd[i];
  uint32_t err = bus.lastError();
  rep->err = err | (ok ? 0u : 0x1000000u);
  if (ok) {
    st |= S_PAGE0_ACK;
    // Follow-on only after an ACK (a dead bus never sees a second
    // transaction). The block 0x0e..0x24 is the F01 basic-query window
    // of a factory-default page 0 (RmiCore.h readIdentity cites
    // rmi_f01.c:138..176: manufacturer at byte 0 of the query, product
    // id at bytes 11..20). A live-configured device may remap F01 —
    // which is why this is recorded raw, matched offline.
    uint8_t off = 0x0e;
    uint8_t q[21] = {};
    qup::Msg m2[2] = {{0x20, false, 1, &off}, {0x20, true, 21, q}};
    if (bus.xfer(m2, 2)) {
      for (unsigned i = 0; i < 21; ++i) rep->f01[i] = q[i];
      st |= S_F01_ACK;
    }
    rep->err2 = bus.lastError();
  } else if (err == qup::E_NACK) {
    st |= S_PAGE0_NACK;
  } else if (err == qup::E_TIMEOUT_STATE || err == qup::E_TIMEOUT_IN ||
             err == qup::E_TIMEOUT_BUS) {
    st |= S_PAGE0_TIMEOUT;
  }

  rep->status = st | S_DONE;
  rep->t_end = now64();

  // 4) Cache discipline (9032a64): flush every dirty staging line so the
  //    warm-reset linear read sees the truth. civac is the safe op here
  //    — the data is written and never re-read.
  for (unsigned o = 0; o < sizeof(Report); o += 64)
    asm volatile("dc civac, %0" ::"r"((uint64_t)(REPORT_BASE + o)));
  asm volatile("dsb sy" ::: "memory");

  for (;;) asm volatile("wfe");
}
