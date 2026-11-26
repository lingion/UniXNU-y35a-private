// SPDX-License-Identifier: BSD-2-Clause-Patent
// RMI4/S3202 object model — the pure, host-testable core for QcomTouch
// (T2.1, plan docs/superpowers/plans/2026-11-05-y35a-touch-driver.md).
//
// Ground truth is Linux v4.9 drivers/input/rmi4 (kernel generation of the
// vendor tree; every constant below cited to /tmp/r9_*.c extracted from
// that tag). The RMI4 spec's "0x0a address window" does not exist — the
// actual paging mechanism is the page-select register, implemented here
// byte-for-byte like the driver:
//
//   rmi_driver.h:39-40       PDT scan window +0x00e9 down to +0x0005,
//                            step 6 (RMI_PDT_ENTRY_SIZE 6, NOT 7)
//   rmi_driver.h:36-37       byte4: function_version mask 0x60 >>5,
//                            interrupt_source_count mask 0x07
//   rmi_driver.h:41          END_OF_PDT: fn 0x00 or 0xff
//   rmi_driver.c rmi_read_pdt_entry + rmi_driver_copy_pdt_to_fd:
//                            buf[0..3] page-relative query/command/
//                            control/data offsets; buf[4] split above;
//                            buf[5] function_number. No irq base — bits
//                            are allocated in scan order (irq_next).
//   rmi_driver.c rmi_scan_pdt_page:433-453: scan window page_start+0xe9
//                            down to +0x005, step -6; the callback's
//                            "break" verdict uses the CURRENT slot's
//                            addr (before the for-step). Stop condition
//                            at :452 is `(bootloader || addr ==
//                            pdt_start) ? BREAK : CONTINUE` — i.e. v4.9
//                            ends the whole scan only when the terminator
//                            sits at the FIRST slot of a page. (Master's
//                            two-consecutive-empty-pages rule is a later
//                            backport; the vendor 3.10-generation tree
//                            predates it, so we do NOT use it.)
//   rmi_driver.c:147-149,363  driver irq status = F01
//                            data_base_addr+1 (num_of_irq_regs bytes);
//                            irq enable/clear words = F01
//                            control_base_addr+1.. .
//   rmi_f01.c:46,138,149,161,176 21-byte basic query (read_block at the
//                            container query base); manufacturer =
//                            queries[0]; product_id = queries[11..20]
//                            (10 B, NUL-terminated; rmi_driver.h
//                            product_id[11]).
//   rmi_f11.c:82-87          device query0 bits: 0x08 q9, 0x10 q11, 0x20 q12
//   rmi_f11.c:1087-1107      device query 0 read alone, then sensor queries
//                            at query+1: q0..q3 block; q5 iff HAS_ABS; q6
//                            iff HAS_REL; q7+q8 iff HAS_GESTURES; q9 iff
//                            has_query9; q10 iff has_touch_shapes (walk
//                            stops — q11/q12/jitter/info2 not read).
//   rmi_f11.c:611-612        nbr_fingers = (q0&7)+1, 5 means 10
//   rmi_f11.c:633-665        f11_2d_construct_data window arithmetic;
//                            abs objects are FIVE bytes fixed (:639 uses
//                            literal 5; comment :202-205 "Only one format
//                            (the kind used here) is supported at this
//                            time") whatever Q5 abs_data_size says.
//   rmi_f11.c:546-561        decode: x=(p0<<4)|(p2&0x0F), y=(p1<<4)|(p2>>4),
//                            z=p4, wx=p3&0x0f, wy=p3>>4. NO 6/8-byte path
//                            in v4.9 (it is master-only, added 2020).
//   rmi_f11.c:563-566        finger state = (f_state[n/4] >> 2*(n%4)) & 3
//   rmi_f11.c:1078-1079      abs irq bit = fn irq_pos, rel = irq_pos+1
//   rmi_f11.c:1152-1162      max_x/max_y: 2-byte LE block at F11 CONTROL
//                            offset 6/8 (F11_CTRL_SENSOR_MAX_X/Y_POS_OFFSET)
//   rmi_f11.c rmi_f11_attention (:1237-1262): when the transport
//                            supplies no attn_data (the I2C block-read
//                            transport never does — rmi_i2c.c has no
//                            interrupt context at all, it is HIL-only),
//                            the handler reads the FULL pkt_size window
//                            from data_base_addr. There is no early exit
//                            and no irq-bit filtering of the window read
//                            in v4.9 (a "glitch" window-clear path is a
//                            master-era addition, absent here); our poll
//                            model mirrors the v4.9 behavior.
//   rmi_i2c.c:47,64-77,130-  page select reg 0xff written {0xff,page} when
//                            the cached page changes; read_block = one
//                            address byte (addr&0xff) + repeated-start
//                            stream read; write_block = [addr&0xff,data...]
//                            in one message (no restart), then page refresh.
//
// Vendor S3202 control-plane snapshot {02 00 00 02 01 02 00 09 05 00 83 40}
// (12 regs, v4.9 RMI_F11_CTRL_REG_COUNT 12): UNVERIFIED PROVENANCE as of
// this writing — the dump artifact is not in the repo or evidence tree
// (git log -S on the byte pattern returns nothing). The plan (docs/
// superpowers/plans/2026-11-05-y35a-touch-driver.md T0) requires an
// on-device capture before this block ships in a boot path; treat these
// as candidate defaults only. Format facts below ARE source-backed:
// v4.9 f11_write_control_regs (rmi_f11.c:741-755) writes all 12 as ONE
// contiguous write_block (rmi_i2c.c:81-127 [addr&0xff,data...] single
// message), threshold bytes sit at ctrl[2]/ctrl[3]
// (RMI_F11_DELTA_X/Y_THRESHOLD = 2/3, rmi_f11.c:430-431) and are applied
// only when the platform supplies nonzero values (:1186-1192); dribble
// clears ctrl[0] bit 6 (:1195), palm det clears ctrl[11] bit 0 (:1198).
// The 09 05 pair in the snapshot sits at ctrl[7]/ctrl[8] — outside the
// driver's threshold slots — vendor-firmware-specific layout, a further
// sign the snapshot needs device confirmation.

#ifndef RMI_CORE_H
#define RMI_CORE_H

#include <stdint.h>
#include <string.h>

namespace rmi {

constexpr uint16_t PAGE_SELECT_REG = 0xff;
constexpr uint16_t PAGE_SIZE_R = 0x0100;
constexpr uint16_t PDT_START = 0xe9;    // scan downward (rmi_driver.h:39)
constexpr uint16_t PDT_END = 0x05;      // (rmi_driver.h:40)
constexpr unsigned PDT_ENTRY_SIZE = 6;  // (rmi_driver.h:35)
constexpr unsigned MAX_FINGERS = 10;
constexpr unsigned F01_BASIC_QUERY_LEN = 21;
constexpr unsigned PRODUCT_ID_LEN = 10;
constexpr unsigned F11_CTRL_REG_COUNT = 12;
constexpr uint16_t MAX_PAGE = 0xff;

constexpr uint8_t SYNAPTICS_MFG_ID = 0x01;

enum FingerState : uint8_t {
  F11_NO_FINGER = 0x00,
  F11_PRESENT = 0x01,
  F11_INACCURATE = 0x02,
  F11_RESERVED = 0x03,
};

// F11 device query 0 bits (rmi_f11.c:82-87 style names)
constexpr uint8_t DQ0_HAS_QUERY9 = 1U << 3, DQ0_HAS_QUERY11 = 1U << 4,
                  DQ0_HAS_QUERY12 = 1U << 5;
// sensor query 0 bits (r9_2d.c RMI_2D_QUERY0_* + rmi_f11.c usage)
constexpr uint8_t Q0_NR_FINGERS_MASK = 0x07, Q0_HAS_REL = 1U << 3,
                  Q0_HAS_ABS = 1U << 4, Q0_HAS_GESTURES = 1U << 5,
                  Q0_CONFIGURABLE = 1U << 7;
constexpr uint8_t Q_NR_ELECTRODES_MASK = 0x7f;
// sensor query 5 (present iff HAS_ABS)
constexpr uint8_t Q5_ABS_DATA_SIZE_MASK = 0x03;
// sensor queries 7/8 (present iff HAS_GESTURES)
constexpr uint8_t Q7_HAS_PINCH = 1U << 6, Q7_HAS_FLICK = 1U << 4;
constexpr uint8_t Q7_HAS_SINGLE_TAP = 1U << 0, Q7_HAS_TAP_AND_HOLD = 1U << 1,
                  Q7_HAS_DOUBLE_TAP = 1U << 2, Q7_HAS_EARLY_TAP = 1U << 3,
                  Q7_HAS_PRESS = 1U << 5, Q7_HAS_CHIRAL = 1U << 7;
constexpr uint8_t Q8_HAS_ROTATE = 1U << 1, Q8_HAS_TOUCH_SHAPES = 1U << 2;
constexpr uint8_t Q8_HAS_PALM_DET = 1U << 0, Q8_HAS_SCROLL_ZONES = 1U << 3,
                  Q8_HAS_IND_SCROLL_ZONES = 1U << 4,
                  Q8_HAS_MF_SCROLL = 1U << 5, Q8_HAS_MF_EDGE_MOTION = 1U << 6,
                  Q8_HAS_MF_SCROLL_INERTIA = 1U << 7;
constexpr uint8_t Q10_NR_TOUCH_SHAPES_MASK = 0x1f;  // v4.9 :133
// driver-level interrupt enable/clear (F11 irq0 = abs, irq1 = rel)
constexpr uint8_t F11_ABS_INT_MASK = 0x01, F11_REL_INT_MASK = 0x02;

struct FnDesc {
  uint8_t function_number = 0;
  uint16_t query = 0, command = 0, control = 0, data = 0;
  uint8_t irq_count = 0;
  uint8_t irq_start = 0;  // accumulated in scan order (v4.9 allocation)
};

struct PdtEntry {
  uint8_t query, command, control, data;
  uint8_t function_version, interrupt_source_count, function_number;
};

// rmi_read_pdt_entry byte split (6-byte entry).
inline void decodePdt(const uint8_t *buf, PdtEntry &e) {
  e.query = buf[0];
  e.command = buf[1];
  e.control = buf[2];
  e.data = buf[3];
  e.interrupt_source_count = buf[4] & 0x07;
  e.function_version = (buf[4] & 0x60) >> 5;
  e.function_number = buf[5];
}

// I2C paging transport — v4.9 rmi_i2c.c read/write_block verbatim shape:
// cached page (probe-time zero), select {0xff,page} ONLY when the target
// page differs, address byte (addr&0xff) written then a repeated-start
// stream read; writes carry [addr&0xff,data...] in ONE message. The
// device-side pointer auto-increments across page edges inside a stream
// and the transport never re-syncs it (v4.9 has no such code; callers
// doing multi-page work issue new block reads, each of which re-anchors
// via the address byte). Bus ducks against I2cBus: bool write(ptr,len)
// and bool readAt(reg,ptr,len). No mutex: our native task is the single
// bus owner (the v4.9 page_mutex guards a shared Linux client; a host
// test and one kernel thread own ours).
template <class Bus>
class RmiXport {
 public:
  static constexpr unsigned MAX_TX = 32;  // covers 12-ctrl block + addr;
                                         // v4.9 grows tx_buf dynamically,
                                         // we cap and refuse (never split)
  explicit RmiXport(Bus &bus) : bus_(bus) {}

  bool selectPage(uint8_t page) {
    if (page == page_) return true;
    uint8_t sel[2] = {uint8_t(PAGE_SELECT_REG), page};
    if (!bus_.write(sel, 2)) return false;  // failed select leaves cache
    page_ = page;                           // untouched (rmi_set_page :77)
    return true;
  }

  bool readBlock(uint16_t addr, uint8_t *buf, unsigned len) {
    if (!selectPage(uint8_t((addr >> 8) & 0xff))) return false;
    return bus_.readAt(uint8_t(addr & 0xff), buf, len);
  }

  bool writeBlock(uint16_t addr, const uint8_t *data, unsigned len) {
    if (len == 0 || len + 1 > MAX_TX) return false;
    if (!selectPage(uint8_t((addr >> 8) & 0xff))) return false;
    uint8_t tx[MAX_TX];
    tx[0] = uint8_t(addr & 0xff);
    memcpy(tx + 1, data, len);
    return bus_.write(tx, len + 1);
  }

  bool write8(uint16_t addr, uint8_t v) { return writeBlock(addr, &v, 1); }
  uint8_t page() const { return page_; }

 private:
  Bus &bus_;
  uint8_t page_ = 0;
};

// PDT walk: v4.9 rmi_scan_pdt/rmi_scan_pdt_page semantics, control flow
// preserved exactly. Terminator = fn 0x00 or 0xff (rmi_driver.h:41). The
// page loop breaks when `first_slot` is true — addr at break equals the
// terminator slot, equal to the scan start iff the page opened empty
// (v4.9 stop rule; master's two-empty-page rule is a later backport and
// deliberately NOT used: the vendor 3.10 line predates it).
// X must provide bool readBlock(uint16_t addr, uint8_t *buf, unsigned len).
template <class X>
unsigned scanPdt(X &x, FnDesc *fns, unsigned max_fns) {
  unsigned nfns = 0, irq_next = 0;
  for (unsigned page = 0; page <= MAX_PAGE; ++page) {
    uint16_t page_start = uint16_t(page << 8);
    bool first_slot = true;  // v4.9's `addr == pdt_start` stop rule,
                             // tracked explicitly: reading addr after the
                             // for-step would underflow (0xe9 - 6) when
                             // the very first slot terminates page 0.
    for (uint16_t addr = PDT_START; addr >= PDT_END; addr -= PDT_ENTRY_SIZE) {
      uint8_t buf[PDT_ENTRY_SIZE + 1];  // byte 6 is the legacy reserved
      if (!x.readBlock(page_start + addr, buf, PDT_ENTRY_SIZE)) return nfns;
      PdtEntry e;
      decodePdt(buf, e);
      if (e.function_number == 0x00 || e.function_number == 0xff) break;
      first_slot = false;
      if (nfns < max_fns) {
        fns[nfns++] = {e.function_number,
                       uint16_t(e.query + page_start),
                       uint16_t(e.command + page_start),
                       uint16_t(e.control + page_start),
                       uint16_t(e.data + page_start), e.interrupt_source_count,
                       uint8_t(irq_next)};
        irq_next += e.interrupt_source_count;
      }
    }
    if (first_slot) break;  // empty page -> whole scan ends (v4.9)
  }
  return nfns;
}

// F01 identity (rmi_f01.c:161,176): manufacturer at queries[0], product
// id at queries[11..20]. v4.9 has NO firmware/build id fields here — the
// identity gate uses manufacturer + product string, both device-probed.
template <class X>
bool readIdentity(X &x, const FnDesc &f01, uint8_t &manufacturer,
                  char product[PRODUCT_ID_LEN + 1]) {
  uint8_t queries[F01_BASIC_QUERY_LEN];
  if (!x.readBlock(f01.query, queries, sizeof queries)) return false;
  manufacturer = queries[0];
  memcpy(product, &queries[11], PRODUCT_ID_LEN);
  product[PRODUCT_ID_LEN] = '\0';
  return true;
}

struct F11Queries {
  uint8_t nr_fingers_cfg = 0;
  uint8_t nr_x_electrodes = 0, nr_y_electrodes = 0;
  bool has_rel = false, has_abs = false, has_gestures = false;
  // Q5 abs_data_size: recorded ONLY. v4.9 fixes the window at 5-byte
  // objects regardless (r9_f11.c:639 literal 5; comment :202-205 "Only
  // one format (the kind used here) is supported at this time"). A
  // non-zero value is logged into identity evidence, never decoded from.
  uint8_t abs_data_size = 0;
  bool query7_nonzero = false, query8_nonzero = false;
  bool query6_nonzero = false;  // v4.9 reads q6 when has_rel (:812-815)
                                // and never uses it; we record nonzero-ness
                                // because it GATES the gesture bytes in the
                                // attention window (:1169-1171 uses only
                                // q7/q8 — the q6 gate is OUR documented
                                // extension, see decodeF11 + the 16G102
                                // vendor dump: ctrl10=0x83 sets SINGLE_TAP,
                                // so query7_nonzero is EXPECTED true).
  bool has_single_tap = false, has_tap_n_hold = false, has_double_tap = false;
  bool has_early_tap = false, has_press = false, has_chiral = false;
  bool has_palm_det = false, has_scroll_zones = false;
  bool has_individual_scroll_zones = false, has_mf_scroll = false;
  bool has_mf_edge_motion = false, has_mf_scroll_inertia = false;
  bool has_pinch = false, has_flick = false, has_rotate = false;
  bool has_touch_shapes = false;
  uint8_t nr_touch_shapes = 0;
  bool has_query9 = false, has_query11 = false;
  // attn extra = nbr_fingers*2 when the PLATFORM declares ACM (v4.9
  // :1170 f11->has_acm is platform data, never a device bit; the S3202
  // platform_data in the vendor tree sets has_acm=true — T0 confirmation
  // item). Rel bytes ride the window exactly when this is set.
  bool has_acm = false;

  unsigned fingers() const {  // r9_f11.c:611-612 (5 means 10)
    return nr_fingers_cfg == 5 ? 10 : unsigned(nr_fingers_cfg) + 1;
  }
};

// Sensor-query walk — rmi_f11.c:1087-1113 byte addresses and conditionals,
// stop-after-q10 (the walk never reads q11/q12/jitter/info2; has_query11
// is sampled only from device query0 as evidence).
template <class X>
bool readF11Queries(X &x, const FnDesc &f11, F11Queries &q) {
  uint8_t dq0 = 0;
  if (!x.readBlock(f11.query, &dq0, 1)) return false;
  q.has_query9 = dq0 & DQ0_HAS_QUERY9;
  q.has_query11 = dq0 & DQ0_HAS_QUERY11;

  uint16_t a = uint16_t(f11.query + 1);  // sensor query 0
  uint8_t buf[4];                        // q0..q3
  if (!x.readBlock(a, buf, 4)) return false;
  q.nr_fingers_cfg = buf[0] & Q0_NR_FINGERS_MASK;
  q.has_rel = buf[0] & Q0_HAS_REL;
  q.has_abs = buf[0] & Q0_HAS_ABS;
  q.has_gestures = buf[0] & Q0_HAS_GESTURES;
  q.nr_x_electrodes = buf[1] & Q_NR_ELECTRODES_MASK;
  q.nr_y_electrodes = buf[2] & Q_NR_ELECTRODES_MASK;
  unsigned size = 4;

  if (q.has_abs) {
    uint8_t q5;
    if (!x.readBlock(uint16_t(a + size), &q5, 1)) return false;
    q.abs_data_size = q5 & Q5_ABS_DATA_SIZE_MASK;
    size++;
  }
  if (q.has_rel) {
    uint8_t q6;
    if (!x.readBlock(uint16_t(a + size), &q6, 1)) return false;
    q.query6_nonzero = q6 != 0;  // v4.9 stores f11_2d_query6 unused;
                                 // nonzero-ness gates our gesture bytes
    size++;
  }
  if (q.has_gestures) {
    uint8_t q78[2];
    if (!x.readBlock(uint16_t(a + size), q78, 2)) return false;
    // v4.9 get_query_parameters gesture decode (:825-880) complete set.
    q.query7_nonzero = q78[0] != 0;
    q.query8_nonzero = q78[1] != 0;
    q.has_single_tap = q78[0] & Q7_HAS_SINGLE_TAP;
    q.has_tap_n_hold = q78[0] & Q7_HAS_TAP_AND_HOLD;
    q.has_double_tap = q78[0] & Q7_HAS_DOUBLE_TAP;
    q.has_early_tap = q78[0] & Q7_HAS_EARLY_TAP;
    q.has_flick = q78[0] & Q7_HAS_FLICK;
    q.has_press = q78[0] & Q7_HAS_PRESS;
    q.has_pinch = q78[0] & Q7_HAS_PINCH;
    q.has_chiral = q78[0] & Q7_HAS_CHIRAL;
    q.has_palm_det = q78[1] & Q8_HAS_PALM_DET;
    q.has_rotate = q78[1] & Q8_HAS_ROTATE;
    q.has_touch_shapes = q78[1] & Q8_HAS_TOUCH_SHAPES;
    q.has_scroll_zones = q78[1] & Q8_HAS_SCROLL_ZONES;
    q.has_individual_scroll_zones = q78[1] & Q8_HAS_IND_SCROLL_ZONES;
    q.has_mf_scroll = q78[1] & Q8_HAS_MF_SCROLL;
    q.has_mf_edge_motion = q78[1] & Q8_HAS_MF_EDGE_MOTION;
    q.has_mf_scroll_inertia = q78[1] & Q8_HAS_MF_SCROLL_INERTIA;
    size += 2;
  }
  if (q.has_query9) {
    uint8_t q9;
    if (!x.readBlock(uint16_t(a + size), &q9, 1)) return false;
    size++;
  }
  if (q.has_touch_shapes) {
    uint8_t q10;
    if (!x.readBlock(uint16_t(a + size), &q10, 1)) return false;
    q.nr_touch_shapes = q10 & Q10_NR_TOUCH_SHAPES_MASK;  // v4.9 :896-897
                                                         // (0x1F, not 0x7F)
    size++;
  }
  return true;
}

// Attention window size — byte-for-byte rmi_f11_2d_construct_data
// arithmetic (r9_f11.c:637-665). This is sensor->pkt_size, and the I2C
// attention read path takes EXACTLY this many bytes: rmi_f11_attention
// (:1244-1248) reads the full pkt_size whenever xport->attn_data is
// absent (the block-transport rmi_i2c.c never sets it — no interrupt
// context exists there), so no query4/has_acm sub-window filtering ever
// applies to us. (f11_2d_construct_data's :1169-1171 attn_size line
// belongs to the relay path only.) 0 when the finger count exceeds the
// model.
inline unsigned gestureRegionBytes(const F11Queries &q) {
  unsigned g = 0;
  if (q.query7_nonzero) g++;
  if (q.query7_nonzero || q.query8_nonzero) g++;
  if (q.has_pinch || q.has_flick || q.has_rotate) {
    g += 3;
    if (!q.has_flick) g--;
    if (!q.has_rotate) g--;
  }
  return g;
}

inline unsigned windowSize(const F11Queries &q) {
  unsigned nf = q.fingers();
  if (nf > MAX_FINGERS) return 0;
  unsigned size = (nf + 3) / 4;
  if (q.has_abs) size += nf * 5;
  if (q.has_rel) size += nf * 2;  // :649-650 unconditional on has_rel
  size += gestureRegionBytes(q);
  if (q.has_touch_shapes)
    size += (unsigned(q.nr_touch_shapes) + 1 + 7) / 8;  // :670-672
  return size;
}

inline unsigned absOffset(const F11Queries &q) {
  return (q.fingers() + 3) / 4;  // after the f_state block
}

// Offset of the gesture region inside the attention window: exactly the
// f11_2d_construct_data cursor walk (:672-685) — f_state, then abs iff
// has_abs, then rel iff has_rel.
inline unsigned gestureOffset(const F11Queries &q) {
  unsigned off = absOffset(q);
  if (q.has_abs) off += q.fingers() * 5;
  if (q.has_rel) off += q.fingers() * 2;
  return off;
}

enum F11Err : unsigned {
  F_OK = 0, F_NO_ABS = 1, F_TOO_MANY_FINGERS = 2,
};

struct Finger {
  unsigned id = 0;
  unsigned x = 0, y = 0;
  unsigned wx = 0, wy = 0;  // p3 nibbles, v4.9 naming
  unsigned w = 0;           // p3 whole-byte evidence
  unsigned z = 0;           // p4
  bool on = false;          // F11_PRESENT
  bool inaccurate = false;  // F11_INACCURATE
};

struct TouchFrame {
  unsigned nfingers = 0;
  Finger f[MAX_FINGERS];
  uint8_t gest1 = 0, gest2 = 0;
};

// Decode one data window. rmi_f11_parse_finger_state (r9_f11.c:563) and
// rmi_f11_abs_pos_process (r9_f11.c:546-557) verbatim; gesture bytes at
// the offsets f11_2d_construct_data assigned (r9_f11.c:677-685).
// Objects are 5 bytes FIXED: abs_data_size never changes the decode
// (matches mainline v4.9 AND master — master only grew 6/8-byte support
// in 2020 with layouts we do not reproduce; on such a device our frames
// would be wrong and T0 capture is the authority to say so, loudly).
inline unsigned decodeF11(const uint8_t *pkt, const F11Queries &q,
                          TouchFrame &fr) {
  unsigned nf = q.fingers();
  if (nf > MAX_FINGERS) return F_TOO_MANY_FINGERS;
  if (!q.has_abs) return F_NO_ABS;
  const uint8_t *f_state = pkt;
  const uint8_t *abs = pkt + absOffset(q);
  fr.nfingers = nf;
  fr.gest1 = 0;
  fr.gest2 = 0;  // reset every frame; v4.9 gesture state is a
                 // read-modify-write of ctrl regs, our frame fields
                 // carry the raw bytes only when the gate delivers them
  for (unsigned n = 0; n < nf; ++n) {
    const uint8_t *p = abs + n * 5;
    unsigned st = (f_state[n / 4] >> (2 * (n % 4))) & 3;
    Finger &fg = fr.f[n];
    fg = Finger{};
    fg.id = n;
    if (st == F11_RESERVED) continue;  // v4.9 :588-591 "Invalid finger
                                       // state" pr_err + skip the object
    // v4.9 rmi_f11_finger_handler: every state except OFF (00) with a
    // track keeps reporting; INACCURATE (10) is defined as "data cannot
    // be used for position" (:525) — the vendor stack still counts it
    // as contact, so on = state != OFF, matching the old suite's
    // "bit0 = on" comment (which was actually right).
    fg.on = st != F11_NO_FINGER;
    fg.inaccurate = st == F11_INACCURATE;
    if (!fg.on) continue;
    fg.x = (unsigned(p[0]) << 4) | (p[2] & 0x0f);
    fg.y = (unsigned(p[1]) << 4) | (unsigned(p[2]) >> 4);
    fg.w = p[3];
    fg.wx = p[3] & 0x0f;
    fg.wy = p[3] >> 4;
    fg.z = p[4];
  }
  // Gesture bytes (r9_f11.c:653-658 walk): gest1 iff query7_nonzero,
  // gest2 iff query7_nonzero || query8_nonzero, at the construct_data
  // cursor (f_state + abs + rel). The region exists in the window under
  // exactly the same conditions, so guarding on its size is tautological
  // safety, not a policy filter: the I2C attention read (rmi_f11_attention
  // :1244-1248, attn_data never set by rmi_i2c) took the full pkt_size.
  if (gestureRegionBytes(q)) {
    const unsigned gbase = gestureOffset(q);
    if (q.query7_nonzero) fr.gest1 = pkt[gbase];
    if (q.query7_nonzero || q.query8_nonzero)
      fr.gest2 = pkt[gbase + (q.query7_nonzero ? 1 : 0)];
  }
  return F_OK;
}

// Vendor S3202 control snapshot (12 regs at F11 control_base_addr — v4.9
// RMI_F11_CTRL_REG_COUNT; see the provenance note above: the byte dump is
// NOT in the evidence tree, treat as candidate defaults until T0 re-capture
// confirms them on the reset-deasserted device). ctrl0_11[7]=0x09
// is the delta-x threshold, [8]=0x05 delta-y (the 09 05 pair sits outside
// the driver's own threshold slots — a further T0 question); [0]=0x02
// enables abs reporting; [10]=0x83, [11]=0x40 device-configured. Written
// as ONE block — v4.9 f11_write_control_regs (rmi_f11.c:741-755) is
// rmi_write_block of all 12; probe-time tweaks (has_dribble clears
// ctrl[0] bit 6, has_palm_det clears ctrl[11] bit 0, rmi_f11.c:1194-1198)
// stay in the T0 record. Identity-gated: applied only after the F01
// manufacturer/product check passes.
constexpr uint8_t F11_CTRL_INIT[F11_CTRL_REG_COUNT] = {
    0x02, 0x00, 0x00, 0x02, 0x01, 0x02, 0x00, 0x09, 0x05, 0x00, 0x83, 0x40};

// driver-level interrupt enable bits within ceil(irq_count/8) bytes (the
// v4.9 mask is a little-endian unsigned-long bitmap; byte k/8 bit k%8 is
// bit k — bitmap_scnread writes them in that order):
// abs at irq_start, rel at irq_start+1 (r9_f11.c:1078-1079).
inline void f11IrqEnables(const FnDesc &f11, uint8_t *en, unsigned n) {
  memset(en, 0, n);
  auto setbit = [&](unsigned bit) {
    unsigned widx = bit / 8, bpos = bit % 8;
    if (widx < n) en[widx] |= uint8_t(1u << bpos);
  };
  if (f11.irq_count > 0) setbit(f11.irq_start);        // abs
  if (f11.irq_count > 1) setbit(unsigned(f11.irq_start) + 1);  // rel
}

// ---- glitch protection (SPEC §4 state machine) ----
// appeared(id) is a glitch if that id was seen in the last window frames;
// lost(id,x,y) is only honored against an active track with |d|<=tol.
class GlitchGuard {
 public:
  // History depth is the fixed 3-frame ring below (SPEC §4 window);
  // the ctor only tunes the lost-event position tolerance.
  explicit GlitchGuard(unsigned tol = 2) : tol_(tol) {}

  // kind: 1 appeared, 0 update, -1 lost. Returns false = drop the event.
  bool accept(unsigned id, unsigned x, unsigned y, int kind) {
    if (id >= MAX_FINGERS) return false;
    if (kind > 0) {
      for (unsigned h = 0; h < sizeof hist_ / sizeof hist_[0]; ++h)
        if (hist_[(head_ + h) % (sizeof hist_ / sizeof hist_[0])][id])
          return false;  // id reused inside the history window
      live_[id] = true;
      seen_[id] = true;
      lx_[id] = x;
      ly_[id] = y;
      return true;
    }
    if (kind < 0) {
      if (!live_[id]) return false;
      unsigned dx = x > lx_[id] ? x - lx_[id] : lx_[id] - x;
      unsigned dy = y > ly_[id] ? y - ly_[id] : ly_[id] - y;
      if (dx > tol_ || dy > tol_) return false;  // lost at a foreign spot
      live_[id] = false;
      return true;
    }
    if (live_[id]) { lx_[id] = x; ly_[id] = y; seen_[id] = true; }
    return live_[id];
  }

  // Commit the frame: the ids seen since the last commit enter history.
  void commitFrame() {
    constexpr unsigned R = sizeof hist_ / sizeof hist_[0];
    head_ = (head_ + R - 1) % R;
    for (unsigned i = 0; i < MAX_FINGERS; ++i) {
      hist_[head_][i] = seen_[i] ? 1 : 0;
      seen_[i] = false;
    }
  }

  bool live(unsigned id) const { return id < MAX_FINGERS && live_[id]; }

 private:
  unsigned tol_;
  bool live_[MAX_FINGERS] = {};
  bool seen_[MAX_FINGERS] = {};
  unsigned lx_[MAX_FINGERS] = {}, ly_[MAX_FINGERS] = {};
  uint8_t hist_[3][MAX_FINGERS] = {};
  unsigned head_ = 0;
};

// ---- ts -> lcd mapping (board facts: ts 1266x2220 vs lcd 720x1280) ----
struct Dim { unsigned w, h; };

// DT-locked panel geometry (docs/board/y35a-facts.md; plan T2.1 requires
// these as constexpr, and the suite asserts the mapping contract against
// them). Device probe may override via the Dim arguments — these are the
// boot defaults, not hard-wired constants of the mapping itself.
constexpr Dim TS_DIM = {1266, 2220};
constexpr Dim LCD_DIM = {720, 1280};

inline void mapPoint(unsigned tx, unsigned ty, const Dim &ts, const Dim &lcd,
                     unsigned &lx, unsigned &ly) {
  lx = tx * lcd.w / ts.w;
  ly = ty * lcd.h / ts.h;
  if (lx > lcd.w - 1) lx = lcd.w - 1;
  if (ly > lcd.h - 1) ly = lcd.h - 1;
}

// ---- boot gate (plan T2.2: identity mismatch refuses, F11 absent refuses) ----
// Pure predicates; NativeTouch composes the refuse/continue decision so the
// host contract test exercises the same functions the boot path will.
inline bool matchIdentity(uint8_t manufacturer, const char *product,
                          uint8_t want_mfg, const char *want_product) {
  if (manufacturer != want_mfg) return false;
  return strncmp(product, want_product, PRODUCT_ID_LEN) == 0;
}

// index of the first descriptor with `number`, or nfns when absent.
inline unsigned findFunction(const FnDesc *fns, unsigned nfns,
                             uint8_t number) {
  for (unsigned i = 0; i < nfns; ++i)
    if (fns[i].function_number == number) return i;
  return nfns;
}

}  // namespace rmi

#endif  // RMI_CORE_H
