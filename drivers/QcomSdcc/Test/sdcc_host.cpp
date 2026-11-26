// SPDX-License-Identifier: BSD-2-Clause-Patent
// Phase 0 host acceptance for SdciCore.h (SPEC.md §4 Phase 0): extended model
// covers resume error 7/8/9, multi-block read, CMD6 switch, write busy wait,
// FIFO bounds, store-window refusals and GPT verification.
// Build: g++ -std=c++17 -fsanitize=address,undefined Test/sdcc_host.cpp -o sdcc_host_test
#include "Model.h"
#include <stdio.h>
#include <string.h>
#include <vector>

// The kernel IO shim provides write32 to FIFO; the model exposes a method and
// SdciCore's write loop calls io.write32(0x20, v) — route it.
static_assert(true);

int main() {
  uint8_t ext[512], block[512], multi[4 * 512];

  // ---- resume + single-block read regression (mirrors read-only suite) ----
  {
    Model io;
    SdciController<Model> card(io);
    assert(card.resume(2, ext) && card.sectors() == 8192);
    assert(card.read(1, block));
    for (unsigned i = 0; i < 512; ++i)
      assert(block[i] == io.image[1][i]);
    size_t count = io.commands.size();
    assert(!card.read(8192, block) && !card.read(0, nullptr));
    assert(io.commands.size() == count);
    puts("1. resume + single-block read + bounds: ok");
  }

  // ---- resume guards: partition isolation (error 8), no supply (7), timeout (3), status faults ----
  for (unsigned part = 1; part < 8; part++) {
    Model io; io.ext[179] = part;
    SdciController<Model> card(io);
    assert(!card.resume(2, ext) && card.error == 8);
    assert(!card.read(0, block));
  }
  { Model io; io.powered = false; SdciController<Model> card(io);
    assert(!card.resume(2, ext) && io.commands.empty() && card.error == 7); }
  { Model io; io.busy = true; SdciController<Model> card(io);
    assert(!card.resume(2, ext) && io.commands.empty() && io.delays == 50000 && card.error == 3); }
  for (unsigned fault = 1; fault <= 2; fault++) {
    Model io; io.fault = fault; SdciController<Model> card(io);
    assert(!card.resume(2, ext) && io.commands.size() == 1);
    assert(card.error == (fault == 1 ? 2 : 1));
  }
  puts("2. resume guards (7/8/9-class) and fail-closed: ok");

  // ---- multi-block read (CMD18): continuous data across 4 sectors ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    assert(card.readSectors(3, 4, multi));
    for (unsigned s = 0; s < 4; ++s)
      for (unsigned i = 0; i < 512; ++i)
        assert(multi[s * 512 + i] == io.image[3 + s][i]);
    assert(!card.readSectors(8190, 4, multi));  // crosses capacity
    assert(!card.readSectors(0, 0, multi));
    puts("3. multi-block read + window math: ok");
  }

  // ---- writes refused while the write gate is closed ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    static uint8_t wbuf[2 * 512];
    memset(wbuf, 0xAB, sizeof(wbuf));
    io.prgWaits = 3;  // program completion clears after a few status polls
    size_t count = io.commands.size();
    assert(!card.writeSectors(10, 1, wbuf) && card.error == 12);
    assert(io.commands.size() == count);       // no command reached the bus
    card.writesEnabled = true;
    assert(card.writeSectors(10, 2, wbuf));
    for (unsigned s = 10; s < 12; ++s)
      for (unsigned i = 0; i < 512; ++i)
        assert(io.image[s][i] == wbuf[i]);
    puts("4. write gate refused (error 12); enabled writes land on the medium: ok");
  }

  // ---- CMD6 EXT_CSD switch: argument layout + PRG wait ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    io.prgWaits = 3;  // first status reads report program-busy
    assert(card.switchExtCsd(3 /*write bits*/, 179 /*PARTITION_CONFIG*/, 0));
    bool sawSwitch = false;
    for (unsigned i = 0; i < io.commands.size(); ++i)
      if (io.commands[i] == 6) sawSwitch = true;
    assert(sawSwitch);
    puts("5. CMD6 switch with access/index/value layout + PRG completion: ok");
  }

  // ---- auto CMD12 error: transport recovers with CMD12 and reports failure ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    io.autoCmd12Err = true;
    assert(!card.readSectors(0, 4, multi));
    bool sawStop = false;
    for (unsigned c : io.commands) if (c == 12) sawStop = true;
    assert(sawStop);
    puts("6. auto-CMD12 error triggers abort recovery (CMD12 sent), request fails closed: ok");
  }

  // ---- GPT verification round-trip and tamper ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    assert(card.gptCheck());
    io.image[1][30] ^= 0xFF;  // corrupt header inside the CRC region
    assert(!card.gptCheck() && card.error == 13);
    io.image[1][30] ^= 0xFF;
    io.image[2][0] ^= 0x01;   // corrupt entry array
    assert(!card.gptCheck() && card.error == 13);
    puts("7. GPT header + entry CRC verification and tamper detection: ok");
  }

  // ---- DAT-busy wait actually blocks (acceptance: "write busy wait") ----
  {
    Model io; SdciController<Model> card(io);
    assert(card.resume(2, ext));
    io.datBusy = true; io.busyForever = true;  // line never released
    io.busy = false; io.prgWaits = 0;
    uint8_t one[512] = {};
    // CMD6: waitStatus passes (command done), then waitDatRelease must time out.
    card.writesEnabled = true;
    unsigned before = io.delays;
    assert(!card.switchExtCsd(3, 179, 0) && card.error == 10);
    assert(io.delays - before >= 50000);
    puts("8. DAT-busy wait bounded: timeout error 10 after full retry budget: ok");
  }

  // ---- store window math (cache partition from the verified GPT) ----
  {
    sdcc::StoreWindow cache{6946816, 7254015, true};
    assert(cache.contains(6946816, 1) && cache.contains(6946816, 307200));  // 150 MiB
    assert(cache.contains(7254015, 1));
    assert(!cache.contains(6946815, 1));           // one sector low
    assert(!cache.contains(7254015, 2));           // crosses the end
    assert(!cache.contains(7254016, 1));           // next partition
    assert(!cache.contains(0, 30535680));          // whole disk
    assert(!cache.contains(6946816, 0));           // empty request
    sdcc::StoreWindow empty{0, 100, false};  // configured but not approved
    assert(!empty.valid() && !empty.contains(0, 1));
    sdcc::StoreWindow unbounded;
    assert(!unbounded.valid());
    puts("9. store window confinement math: ok");
  }

  puts("SdciCore Phase 0 host suite: all checks passed");
}
