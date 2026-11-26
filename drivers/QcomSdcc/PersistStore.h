// SPDX-License-Identifier: BSD-2-Clause-Patent
// Persistent-store contract over the sdhc1 transport (SPEC 3.7 Phase 2).
// RamBlock's PersistOverlay.h calls the six native_ufs_store_* symbols with
// units of persist::kBlock (4096 B); this template maps that window onto
// absolute card sectors inside ONE partition located by exact GPT label —
// never a hardcoded LBA range — and confines every access to it. Writes
// require the approved flag (user sign-off gate, SPEC Phase 2) AND the
// transport's write gate; without either, requests refuse before touching
// the bus. Durability: write returns only after the transport's PRG wait,
// which is the promise PersistOverlay.h encodes.
#ifndef QCOMSDCC_PERSISTSTORE_H
#define QCOMSDCC_PERSISTSTORE_H
#include "SdciCore.h"
#include <string.h>

namespace sdcc {

template <class CARD> class SdccStore {
 public:
  static constexpr uint64_t kBlockSectors = 8;  // 4096 / 512

  struct Config {
    const char *label = "cache";  // SPEC 3.7 store-window choice (owner)
    bool approved = false;        // false until explicit user sign-off
  } config;

  void attach(CARD *c) { card = c; }
  void detach() { card = nullptr; opened = false; }
  bool isOpen() const { return opened; }
  uint64_t firstSector() const { return partition.first; }
  const uint8_t *partitionGuid() const { return partition.typeGuid; }

  // 0 keeps RamBlock on the volatile disk; 2 = read-write direct mode
  // (PersistOverlay answers page I/O through the window).
  unsigned mode() const {
    return card && config.approved && card->readyForStore() ? 2u : 0u;
  }

  unsigned gptCheck() {
    if (!card) return 0xff;
    return card->gptCheck() ? 0u : card->error;
  }

  bool open(uint64_t blocks, uint64_t *firstOut, const char **why) {
    if (!card || !card->readyForStore()) { *why = "sdhc1 card not resumed"; return false; }
    if (!config.approved) { *why = "store window not user-approved"; return false; }
    uint32_t first = 0, last = 0;
    uint8_t guid[16] = {};
    if (!card->findPartition(config.label, &first, &last, guid)) {
      *why = "store partition not uniquely present in a verified GPT";
      return false;
    }
    memcpy(partition.typeGuid, guid, 16);
    uint64_t sectors = 0;
    if (!windowSectors(blocks, &sectors) || sectors > uint64_t(last) + 1 - first) {
      *why = "persist window exceeds the cache partition";  // labels never exceed; sized in SPEC 3.7
      return false;
    }
    partition.first = first;
    partition.last = last;
    windowBlocks = blocks;
    *firstOut = first;
    opened = true;
    return true;
  }

  bool read(uint64_t block, uint32_t count, void *dst) {
    uint64_t sector = 0;
    if (!bounded(block, count, &sector) || !card) return false;
    return card->readSectors(static_cast<uint32_t>(sector),
                             static_cast<unsigned>(count * kBlockSectors),
                             static_cast<uint8_t *>(dst));
  }

  bool write(uint64_t block, uint32_t count, const void *src) {
    uint64_t sector = 0;
    if (!bounded(block, count, &sector) || !card) return false;
    if (!config.approved || !card->writesAllowed()) return false;  // double gate
    return card->writeSectors(static_cast<uint32_t>(sector),
                              static_cast<unsigned>(count * kBlockSectors),
                              static_cast<const uint8_t *>(src));
  }

  // The transport write already waited for card programming completion
  // (CMD13 state leaves PROGRAMMING, DAT released) — nothing further is queued.
  bool sync() { return opened && card != nullptr; }

 private:
  CARD *card = nullptr;
  bool opened = false;
  uint64_t windowBlocks = 0;
  StorePartition partition;

  static bool windowSectors(uint64_t blocks, uint64_t *out) {
    if (!blocks || blocks > UINT64_MAX / kBlockSectors) return false;
    *out = blocks * kBlockSectors;
    return true;
  }
  bool bounded(uint64_t block, uint32_t count, uint64_t *sector) const {
    if (!opened || !count || block >= windowBlocks ||
        count > windowBlocks - block) return false;  // overflow-safe containment
    if (block > UINT64_MAX / kBlockSectors) return false;
    *sector = partition.first + block * kBlockSectors;
    return true;
  }
};

} // namespace sdcc
#endif
