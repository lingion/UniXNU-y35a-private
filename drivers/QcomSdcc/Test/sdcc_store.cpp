// SPDX-License-Identifier: BSD-2-Clause-Patent
// Phase 2 host acceptance for PersistStore.h (SPEC.md §4): the store window
// is located by GPT label (no hardcoded LBAs), confined to the partition,
// double-gated for writes, and answers RamBlock's persist::kBlock units.
// Build: g++ -std=c++17 -fsanitize=address,undefined Test/sdcc_store.cpp -o sdcc_store_test
#include "../PersistStore.h"
#include "Model.h"
#include <stdio.h>
#include <string.h>
#include <vector>

int main() {
  uint8_t ext[512];

  // ---- mode gate: no card / unapproved = 0 (volatile disk), approved+resumed = 2 ----
  {
    Model io;
    SdciController<Model> card(io);
    sdcc::SdccStore<SdciController<Model>> store;
    assert(store.mode() == 0);  // nothing attached
    store.attach(&card);
    assert(store.mode() == 0);  // card not resumed yet
    assert(card.resume(2, ext));
    assert(store.mode() == 0);  // resumed but not user-approved
    store.config.approved = true;
    assert(store.mode() == 2);  // read-write direct (SPEC Q2: cache partition)
    puts("1. mode gate: volatile until approved, then direct mode: ok");
  }

  // ---- open refusals: unapproved, oversized window, unknown label ----
  {
    Model io; SdciController<Model> card(io);
    sdcc::SdccStore<SdciController<Model>> store;
    store.attach(&card);
    assert(card.resume(2, ext));
    const char *why = "";
    uint64_t first = 0;
    assert(!store.open(20, &first, &why) && strstr(why, "not user-approved"));
    store.config.approved = true;
    assert(!store.open(70, &first, &why) && strstr(why, "exceeds"));  // 70*8 > 544 sectors
    sdcc::SdccStore<SdciController<Model>> wrong;
    wrong.attach(&card);
    wrong.config.approved = true;
    wrong.config.label = "motorsports";  // absent from the fixture GPT
    assert(!wrong.open(20, &first, &why) && strstr(why, "uniquely present"));
    assert(store.open(68, &first, &why));  // exactly the partition fits
    assert(first == 200);
    assert(store.firstSector() == 200);
    assert(store.partitionGuid()[0] == 0xA5);  // located the labeled entry, not a guess
    puts("2. open refusals (approval, size, label) + exact partition location: ok");
  }

  // ---- read round-trip through the window mapping ----
  {
    Model io; SdciController<Model> card(io);
    sdcc::SdccStore<SdciController<Model>> store;
    store.attach(&card);
    assert(card.resume(2, ext));
    store.config.approved = true;
    const char *why = "";
    uint64_t first = 0;
    assert(store.open(68, &first, &why));
    uint8_t buf[4096], ref[4096];
    assert(store.read(5, 1, buf));  // block 5 = card sectors 200+40 .. 200+47
    for (unsigned s = 0; s < 8; ++s)
      memcpy(ref + s * 512, io.image[240 + s], 512);
    assert(memcmp(buf, ref, 4096) == 0);
    assert(!store.read(68, 1, buf));   // one block past the window
    assert(!store.read(0, 0, buf));    // empty request
    assert(!store.read(67, 2, buf));   // crosses the end
    puts("3. window read mapping to absolute sectors + bounds refusal: ok");
  }

  // ---- write double gate and durability path ----
  {
    Model io; SdciController<Model> card(io);
    sdcc::SdccStore<SdciController<Model>> store;
    store.attach(&card);
    assert(card.resume(2, ext));
    store.config.approved = true;
    const char *why = "";
    uint64_t first = 0;
    assert(store.open(68, &first, &why));
    uint8_t page[4096];
    memset(page, 0xC5, sizeof(page));
    size_t cmdCount = io.commands.size();
    assert(!store.write(3, 1, page));                 // transport write gate closed
    assert(io.commands.size() == cmdCount);           // nothing reached the bus
    card.writesEnabled = true;
    io.prgWaits = 3;
    assert(store.write(3, 1, page));                  // program + PRG wait
    for (unsigned s = 0; s < 8; ++s)
      for (unsigned i = 0; i < 512; ++i) assert(io.image[224 + s][i] == 0xC5);
    uint8_t back[4096];
    assert(store.read(3, 1, back) && memcmp(back, page, 4096) == 0);
    assert(!store.write(70, 1, page));  // outside the window, refused pre-bus
    assert(store.sync());
    puts("4. write double gate, landed bytes verified, sync after PRG: ok");
  }

  // ---- detach closes the window (RamBlock degraded path parity) ----
  {
    Model io; SdciController<Model> card(io);
    sdcc::SdccStore<SdciController<Model>> store;
    store.attach(&card);
    assert(card.resume(2, ext));
    store.config.approved = true;
    const char *why = "";
    uint64_t first = 0;
    assert(store.open(68, &first, &why));
    store.detach();
    uint8_t buf[4096];
    assert(store.mode() == 0 && !store.read(0, 1, buf) && !store.isOpen());
    puts("5. detach: window sealed, mode falls back to volatile: ok");
  }

  puts("PersistStore Phase 2 host suite: all checks passed");
}
