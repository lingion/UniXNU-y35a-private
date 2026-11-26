// SPDX-License-Identifier: BSD-2-Clause-Patent
// SDHCI transport core for the MSM8916 sdhc1 controller (vivo Y35A eMMC).
// Resumes the card configured by lk2nd; cold init is a separate, later path.
// Register facts and the resume sequence are device-proven; the extensions
// (multi-block, CMD6/CMD12/CMD13, writes) follow LK sdhci/mmc bit definitions
// (platform/msm_shared/include/sdhci.h, mmc.c:1198) re-derived here from the
// SoC data sheet layout, not copied. Template<class IO> so the exact code runs
// both in the host model tests and in the kernel driver.
#ifndef QCOMSDCC_SDICORE_H
#define QCOMSDCC_SDICORE_H
#include <stdint.h>
#include <string.h>

namespace sdcc {

// Transfer directions for the engine. NONE: no data line use.
// RD1/RD_MULTI/WR_MULTI map onto the controller's MCI-flavoured TRANS_MODE
// bits (BIT(4)=read, BIT(5)=multi, BIT(1)=block count, BIT(2)=auto CMD12),
// matching the read-only single-block 0x10 proven on device.
enum Trans : uint16_t {
  TRANS_NONE = 0x00,
  TRANS_RD1 = 0x10,
  TRANS_RD_MULTI = 0x10 | 0x20 | 0x02 | 0x04,
  TRANS_WR_MULTI = 0x20 | 0x02 | 0x04,
};

// A CRC32 (IEEE, reflected, polynomial 0xEDB88320) over a GPT header with its
// own checksum field zeroed, and over the partition entry array.
inline uint32_t crc32(const uint8_t *p, unsigned n) {
  static uint32_t table[256];
  static bool init = false;
  if (!init) {
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t v = i;
      for (unsigned k = 0; k < 8; ++k) v = (v & 1) ? 0xEDB88320U ^ (v >> 1) : v >> 1;
      table[i] = v;
    }
    init = true;
  }
  uint32_t c = 0xffffffffU;
  for (unsigned i = 0; i < n; ++i) c = table[(c ^ p[i]) & 0xff] ^ (c >> 8);
  return ~c;
}

// Store window math for the persistent Data overlay (SPEC 3.7): writes
// outside the approved partition window are refused before touching the bus.
struct StoreWindow {
  uint32_t first = 0, last = 0;  // inclusive sector range (cache partition)
  bool enabled = false;          // set only with user approval (SPEC Phase 2)
  bool valid() const { return enabled && first <= last; }
  bool contains(uint32_t start, unsigned count) const {
    return valid() && start >= first && count > 0 &&
           uint64_t(start) + count - 1 <= last;
  }
};

// A partition located by label in the verified GPT entry array, with its
// inclusive sector range and 16-byte type GUID (PersistStore.h consumer).
struct StorePartition {
  uint32_t first = 0, last = 0;
  uint8_t typeGuid[16] = {};
};

} // namespace sdcc

template <class IO> class SdciController {
  IO &io;
  uint32_t capacity = 0;
  uint16_t rca = 0;
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
  // DAT-line release after a busy (R1B / program) operation: PRESENT bit 3.
  bool waitDatRelease() {
    for (unsigned i = 0; i < 50000; ++i) {
      if (!(io.read32(0x24) & (1U << 3))) return true;
      io.delay();
    }
    error = 10; return false;
  }

 public:
  unsigned error = 0, lastCommand = 0;
  uint32_t status = 0, response = 0;
  bool writesEnabled = false;  // Phase 1 ships with writes refused (error 12).

  explicit SdciController(IO &port) : io(port) {}

  // index 12/13/6 -> no data; 17 single read; 18 multi read; 25 multi write.
  // Blocks 1..65535; data == nullptr only valid with TRANS_NONE.
  bool command(unsigned index, uint32_t argument, sdcc::Trans trans,
               uint8_t *data, unsigned blocks) {
    if (!ready && !(index == 5 || index == 7 || index == 8)) { error = 4; return false; }
    if (index == 25 && !writesEnabled) { error = 12; return false; }
    if (blocks == 0 || blocks > 65535) { error = 4; return false; }
    if ((trans != sdcc::TRANS_NONE) != (data != nullptr)) { error = 4; return false; }
    bool multi = trans == sdcc::TRANS_RD_MULTI || trans == sdcc::TRANS_WR_MULTI;
    if (multi && (index != 18 && index != 25)) { error = 4; return false; }
    error = 0; lastCommand = index;
    if (!idle()) return false;
    io.write32(0x30, 0xffffffffU);
    io.write8(0x2e, 0xe);
    if (data) {
      io.write32(0x04, (blocks << 16) | 512);  // BLKSIZE:0x04 BLKCNT:0x06
      // Match LK's read-side DLL policy, preserving its tuned phase.
      io.write32(0x100, (io.read32(0x100) | (1U << 17)) & ~(1U << 19));
    }
    io.write32(0x08, argument);
    io.write16(0x0c, static_cast<uint16_t>(trans));
    // Command register encodings are byte-identical to the device-proven
    // read-only path: 0x1b for no-data R1/R1B (index<<8 | busy-response 0b11
    // | CRC 0x8 | idx 0x10) and 0x3a when a PIO data phase follows (0x20).
    io.write16(0x0e, static_cast<uint16_t>((index << 8) | (data ? 0x3a : 0x1b)));
    if (!waitStatus(1)) return false;
    response = io.read32(0x10);
    io.write32(0x30, 1);
    // The error mask is the probed R1 filter for configuration/transfer
    // commands. CMD13 carries the device state field, whose programming and
    // reserved bits the mask would misread, so it is checked by callers.
    if (index != 13 && (response & 0xfdffa080U)) { error = 5; return false; }
    if (data) {
      if (trans == sdcc::TRANS_WR_MULTI) {
        for (unsigned i = 0; i < blocks * 512; i += 4) {
          uint32_t v = 0;
          for (unsigned b = 0; b < 4; ++b) v |= uint32_t(data[i + b]) << (8 * b);
          io.write32(0x20, v);
        }
        if (!waitStatus(2)) { recover(index); return false; }
        io.write32(0x30, 2);
      } else {
        if (!waitStatus(0x20)) { recover(index); return false; }
        if (!(io.read32(0x24) & (1U << 11))) { recover(index); error = 6; return false; }
        for (unsigned i = 0; i < blocks * 512; i += 4) {
          uint32_t value = io.read32(0x20);
          for (unsigned b = 0; b < 4; ++b) data[i + b] = value >> (8 * b);
        }
        io.write32(0x30, 0x20);
        if (!waitStatus(2)) { recover(index); return false; }
        io.write32(0x30, 2);
      }
      if (status & 0x100) { recover(index); return false; }  // auto-CMD12 error
      if (!waitDatRelease()) { recover(index); return false; }
    }
    return idle();
  }

  // Abort an unfinished data transfer (CMD12, R1B, no data phase).
  void recover(unsigned failedIndex) {
    if (failedIndex == 18 || failedIndex == 25) {
      bool savedReady = ready;
      command(12, 0, sdcc::TRANS_NONE, nullptr, 1);
      ready = savedReady != 0;
    }
  }

  bool getCardStatus(uint32_t *out) {
    if (!command(13, uint32_t(rca) << 16, sdcc::TRANS_NONE, nullptr, 1)) return false;
    *out = response;
    return true;
  }

  // EXT_CSD switch, LK mmc.c:1217 argument layout: [25:24] access, [23:16]
  // index, [15:8] value; R1B busy, then program completion is the CMD13
  // device state field (LK mmc.h:278, [12:9]) leaving PROGRAMMING (7) in TRAN (4).
  bool switchExtCsd(unsigned access, unsigned index, unsigned value) {
    if (!command(6, (access << 24) | (index << 16) | (value << 8),
                 sdcc::TRANS_NONE, nullptr, 1)) return false;
    if (!waitDatRelease()) return false;
    for (unsigned i = 0; i < 50000; ++i) {
      uint32_t cs = 0;
      if (!getCardStatus(&cs)) return false;
      // JEDEC device state field (LK mmc.h:278): wait until PROGRAMMING (7)
      // clears; LK additionally requires TRAN (4) after a switch.
      unsigned state = (cs >> 9) & 0xfU;
      if (state != 7U) {
        if (cs & 0x80U) { error = 11; return false; }  // switch-func error (LK mmc.c:1261)
        return state == 4U;
      }
      io.delay();
    }
    error = 10; return false;
  }

  bool resume(uint16_t address, uint8_t *extCsd) {
    ready = false; capacity = 0; rca = address;
    if (!address || !extCsd) { error = 4; return false; }
    io.enableHostMode();
    // The bootloader owns regulator, clocks and tuning. Refuse an absent clock
    // or power supply rather than silently assuming a usable handoff.
    if ((io.read16(0x2c) & 7) != 7 || !(io.read8(0x29) & 1)) { error = 7; return false; }
    io.write32(0x38, 0);  // Poll only, no CPU interrupt signal.
    io.write32(0x34, 0x03ff0033U);
    if (!command(5, uint32_t(address) << 16, sdcc::TRANS_NONE, nullptr, 1) ||
        !command(7, uint32_t(address) << 16, sdcc::TRANS_NONE, nullptr, 1) ||
        !command(8, 0, sdcc::TRANS_RD1, extCsd, 1)) return false;
    // Do not expose boot partitions or RPMB as the user area.
    if (extCsd[179] & 7) { error = 8; return false; }
    capacity = uint32_t(extCsd[212]) | uint32_t(extCsd[213]) << 8 |
               uint32_t(extCsd[214]) << 16 | uint32_t(extCsd[215]) << 24;
    if (!capacity) { error = 9; return false; }
    ready = true; return true;
  }

  uint32_t sectors() const { return capacity; }
  bool readyForStore() const { return ready; }
  bool writesAllowed() const { return writesEnabled; }

  bool read(uint32_t sector, uint8_t *data) {
    if (!ready || !data || sector >= capacity) { error = 4; return false; }
    if (command(17, sector, sdcc::TRANS_RD1, data, 1)) return true;
    ready = false;  // No retry against a controller left in an unknown state.
    return false;
  }
  bool readSectors(uint32_t start, unsigned count, uint8_t *data) {
    if (!ready || !data || !count ||
        uint64_t(start) + count > capacity) { error = 4; return false; }
    while (count) {
      unsigned chunk = count > 65535 ? 65535 : count;
      if (!command(18, start, sdcc::TRANS_RD_MULTI, data, chunk)) {
        ready = false; return false;
      }
      start += chunk; data += chunk * 512; count -= chunk;
    }
    return true;
  }
  bool writeSectors(uint32_t start, unsigned count, const uint8_t *data) {
    if (!ready || !data || !count ||
        uint64_t(start) + count > capacity) { error = 4; return false; }
    if (!writesEnabled) { error = 12; return false; }
    while (count) {
      unsigned chunk = count > 65535 ? 65535 : count;
      if (!command(25, start, sdcc::TRANS_WR_MULTI, const_cast<uint8_t *>(data), chunk)) {
        ready = false; return false;
      }
      // Durability contract (PersistOverlay.h): return only once the blocks
      // are on the medium — DAT released, then the CMD13 device state field
      // (LK mmc.h:278) leaves PROGRAMMING (7).
      for (unsigned i = 0; i < 50000; ++i) {
        uint32_t cs = 0;
        if (!getCardStatus(&cs)) { ready = false; return false; }
        if (((cs >> 9) & 0xfU) != 7U) break;  // programming complete
        io.delay();
        if (i == 49999) { error = 10; ready = false; return false; }
      }
      start += chunk; data += chunk * 512; count -= chunk;
    }
    return true;
  }

  // GPT sanity for the store window (SPEC 3.7 gpt_check): protective MBR
  // signature at LBA0, header + entry-array CRC32 at LBA1.
  bool gptCheck() {
    uint8_t sector[512];
    if (!read(0, sector)) return false;
    if (sector[510] != 0x55 || sector[511] != 0xAA) { error = 13; return false; }
    if (!read(1, sector)) return false;
    const char *sig = "EFI PART";
    for (unsigned i = 0; i < 8; ++i)
      if (sector[i] != (uint8_t)sig[i]) { error = 13; return false; }
    uint32_t stored = u32(sector + 16);
    uint32_t headerSize = u32(sector + 12);
    if (headerSize < 92 || headerSize > 512) { error = 13; return false; }
    sector[16] = sector[17] = sector[18] = sector[19] = 0;
    if (sdcc::crc32(sector, headerSize) != stored) { error = 13; return false; }
    // GPT layout: 72=PartitionEntryArrayLBA, 80=NumberOfEntries,
    // 84=SizeOfEntry, 88=PartitionEntryArrayCRC32.
    uint32_t arrayLba = u32(sector + 72);  // low 32 bits; entries are < 4 GiB in LBA on this card
    uint32_t numEntries = u32(sector + 80);
    uint32_t sizeEntry = u32(sector + 84);
    uint32_t arrayCrc = u32(sector + 88);
    if (numEntries == 0 || sizeEntry < 128 || sizeEntry > 512 ||
        uint64_t(numEntries) * sizeEntry > 16u * 1024 * 1024) { error = 13; return false; }
    uint32_t acc = 0xffffffffU;
    // CRC over the whole entry array, streaming sector by sector.
    unsigned total = numEntries * sizeEntry;
    for (unsigned done = 0; done < total; done += 512) {
      uint32_t lba = arrayLba + done / 512;
      if (!read(lba, sector)) return false;
      unsigned take = total - done < 512 ? total - done : 512;
      for (unsigned i = 0; i < take; ++i) {
        acc ^= sector[i];
        for (unsigned k = 0; k < 8; ++k) acc = (acc >> 1) ^ (0xEDB88320U & -(acc & 1));
      }
    }
    if ((~acc) != arrayCrc) { error = 13; return false; }
    return true;
  }

 private:
  static uint32_t u32(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
  }
  // GPT entry names are UTF-16LE at offset 56; ASCII-substring compare is
  // enough for the all-lowercase partition labels this board uses.
  static bool entryNameIs(const uint8_t *entry, const char *name) {
    unsigned i = 0;
    for (;; ++i) {
      uint16_t unit = uint16_t(entry[56 + 2 * i]) | uint16_t(entry[56 + 2 * i + 1]) << 8;
      if (unit != (uint16_t)name[i]) return false;
      if (!name[i]) return true;
    }
  }

 public:
  // Locate one partition by exact label inside the entry array (GPT layout:
  // header at LBA1; 72=EntryArrayLBA, 80=NumberOfEntries, 84=SizeOfEntry).
  // Returns false unless exactly one entry matches, with its inclusive
  // first/last sector and 16-byte type GUID recorded.
  bool findPartition(const char *name, uint32_t *first, uint32_t *last,
                     uint8_t typeGuid[16]) {
    uint8_t header[512];
    if (!read(1, header)) return false;
    uint32_t arrayLba = u32(header + 72);
    uint32_t numEntries = u32(header + 80);
    uint32_t sizeEntry = u32(header + 84);
    if (!numEntries || sizeEntry < 128 || sizeEntry > 512 ||
        uint64_t(numEntries) * sizeEntry > 16u * 1024 * 1024) { error = 14; return false; }
    unsigned matches = 0;
    uint8_t entry[512];
    uint32_t hitFirst = 0, hitLast = 0;
    uint8_t hitGuid[16] = {};
    for (uint32_t i = 0; i < numEntries; ++i) {
      uint32_t lba = arrayLba + (i * sizeEntry) / 512;
      unsigned within = (i * sizeEntry) % 512;
      if (within + sizeEntry > 512) { error = 14; return false; }  // entry crossing sectors
      if (!read(lba, entry)) return false;
      const uint8_t *e = entry + within;  // the entry itself, not the sector start
      uint64_t startLba = uint64_t(e[32]) | uint64_t(e[33]) << 8 |
                          uint64_t(e[34]) << 16 | uint64_t(e[35]) << 24;
      uint64_t endLba = uint64_t(e[40]) | uint64_t(e[41]) << 8 |
                        uint64_t(e[42]) << 16 | uint64_t(e[43]) << 24;
      if (e[36] || e[37] || e[38] || e[39] || e[44] || e[45] || e[46] || e[47])
        continue;  // LBA beyond 32 bits — not addressable by this card's ranges
      if (startLba > capacity || endLba + 1 > capacity) continue;  // not user area
      if (entryNameIs(e, name)) {
        ++matches;
        hitFirst = static_cast<uint32_t>(startLba);
        hitLast = static_cast<uint32_t>(endLba);  // cache-scale partitions fit u32
        memcpy(hitGuid, e, 16);
      }
    }
    if (matches != 1) { error = 14; return false; }
    *first = hitFirst;
    *last = hitLast;
    memcpy(typeGuid, hitGuid, 16);
    return true;
  }
};

#endif
