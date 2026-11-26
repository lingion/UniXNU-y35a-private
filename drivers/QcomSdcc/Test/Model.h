// SPDX-License-Identifier: BSD-2-Clause-Patent
// Shared host card model for the QcomSdcc host suites. Mirrors the
// measured MSM8916 sdhc1 handoff state (SPEC 2.2) and answers the
// SdciController register protocol for unit acceptance.
#ifndef QCOMSDCC_TEST_MODEL_H
#define QCOMSDCC_TEST_MODEL_H
#include "../SdciCore.h"
#include <assert.h>
#include <vector>

struct Model {
  static constexpr unsigned Sectors = 1024;
  uint8_t image[Sectors][512];
  uint8_t ext[512] = {};
  uint32_t status = 0, argument = 0, offset = 0;
  uint32_t cardStatus = 0x900;  // TRAN | READY_FOR_DATA
  unsigned delays = 0, fault = 0, prgWaits = 0;
  bool powered = true, active = false, busy = false, datBusy = false;
  bool expectWrite = false, autoCmd12Err = false, busyForever = false;
  std::vector<unsigned> commands;
  uint16_t transMode = 0;
  unsigned blocks = 1;
  bool dllReads = true;

  Model() {
    ext[213] = 0x20;  // capacity 8192 sectors, as in the read-only tests
    for (unsigned s = 0; s < Sectors; ++s)
      for (unsigned i = 0; i < 512; ++i)
        image[s][i] = uint8_t(s * 7 + i * 13 + 3);
    buildGpt();
  }
  void buildGpt() {
    uint8_t *mbr = image[0];
    memset(mbr, 0, 512);
    mbr[510] = 0x55; mbr[511] = 0xAA; mbr[0] = 0xEB; mbr[2] = 0x90;  // boot sig
    mbr[4] = 0xEE;  // protective GPT type at first entry
    uint8_t *h = image[1];
    memset(h, 0, 512);
    memcpy(h, "EFI PART", 8);
    h[8] = 0x00;  // revision
    put32(h + 16, 0);  // checksum field zero while the fixture builds
    put32(h + 12, 92);   // header size
    put32(h + 72, 2);    // entry array LBA
    put32(h + 80, 2);    // number of entries
    put32(h + 84, 128);  // entry size
    uint8_t *e = image[2];
    memset(e, 0, 512 * 2);
    e[0] = 0x00;         // first entry type GUID starts zero in our fixture
    put32(e + 32, 6);    // starting LBA of a fake window
    put32(e + 40, 100);  // last LBA
    putName(e, "unused");
    uint8_t *c = e + 128;  // second entry: the store partition under test
    c[0] = 0xA5;           // distinct type GUID byte so tests can compare
    put32(c + 32, 200);    // cache partition starts at sector 200
    put32(c + 40, 743);    // 544 sectors = 68 blocks = a 20-block window fits, 70-block does not
    putName(c, "cache");
    uint32_t arrayCrc = sdcc::crc32(e, 256);
    put32(h + 88, arrayCrc);
    uint32_t headerCrc = sdcc::crc32(h, 92);
    put32(h + 16, headerCrc);
  }
  static void put32(uint8_t *p, uint32_t v) {
    for (unsigned i = 0; i < 4; ++i) p[i] = uint8_t(v >> (8 * i));
  }
  static void putName(uint8_t *entry, const char *name) {  // GPT names are UTF-16LE at 56
    for (unsigned i = 0; name[i]; ++i) entry[56 + 2 * i] = uint8_t(name[i]);
  }

  uint32_t read32(unsigned r) {
    if (r == 0x30) return status;
    if (r == 0x24)
      return (busy ? 3u : 0u) | (datBusy ? 8u : 0u) |
             (active ? (1u << 11) : 0u) | (expectWrite && active ? (1u << 10) : 0u);
    if (r == 0x10) return r1Response();
    if (r == 0x100) return 0x7a76400;  // DLL_CONFIG handoff value
    if (r == 0x20) {
      assert(active && offset < blocks * 512);
      unsigned sector = argument % Sectors;
      uint32_t value = 0;
      for (unsigned b = 0; b < 4; ++b) {
        uint8_t byte;
        if (commands.back() == 8) byte = ext[offset + b];
        else if (expectWrite) byte = 0;  // writes come from the host side
        else byte = image[(sector + offset / 512) % Sectors][offset % 512 + b];
        value |= uint32_t(byte) << (8 * b);
      }
      offset += 4;
      if (offset == blocks * 512) {
        status |= 2 | (autoCmd12Err ? 0x100u : 0u);
        active = false;
      }
      return value;
    }
    return 0;
  }
  uint32_t r1Response() {
    unsigned cmd = commands.back();
    if (cmd == 13) return cardStatus;
    return 0x900;
  }
  uint16_t read16(unsigned r) {
    if (r == 0x2c) return powered ? 7 : 0;
    return 0;
  }
  uint8_t read8(unsigned r) {
    if (r == 0x29) return powered ? 0xb : 0;
    if (r == 0x28) return 0xb3;
    return 0;
  }
  void write32(unsigned r, uint32_t v) {
    if (r == 0x30) status &= ~v;
    if (r == 0x08) argument = v;
    if (r == 0x04) blocks = v >> 16;  // BLKSIZE:BLKCNT as one 32-bit write
    if (r == 0x20) writeFifo(v);      // data FIFO, write direction
  }
  void write16(unsigned r, uint16_t v) {
    if (r == 0x0c) transMode = v;
    if (r != 0x0e) return;
    unsigned cmd = v >> 8;
    commands.push_back(cmd); offset = 0;
    // R1B (CMD6, CMD12) and completed CMD25 programs hold the DAT line busy.
    if (cmd == 6 || (v & 0x03) == 3) datBusy = true;
    expectWrite = (v & 0x20) && !(transMode & 0x10);
    active = (v & 0x20) != 0;
    if (fault == 1) { status = 0x208000; return; }
    if (fault == 2) { status = 0; return; }
    if (fault == 3 && cmd == 12) { status = 0x20000; return; }  // abort itself times out
    status = 1 | (active ? 0x20 : 0);
    if (!active) {
      // command-only completion already signalled via status bit 0.
    }
  }
  void write8(unsigned, uint8_t) {}
  void writeFifo(uint32_t value) {
    assert(active && expectWrite && offset < blocks * 512);
    unsigned sector = argument % Sectors;
    for (unsigned b = 0; b < 4; ++b) {
      image[(sector + offset / 512) % Sectors][offset % 512 + b] = uint8_t(value >> (8 * b));
    }
    offset += 4;
    if (offset == blocks * 512) {
      status |= 2 | (autoCmd12Err ? 0x100u : 0u);
      active = false;
      if (commands.back() == 25) { cardStatus = (7u << 9); datBusy = true; }  // PROGRAMMING state
    }
  }
  void delay() {
    ++delays;
    if (datBusy && !busyForever && ++busyTicks >= 3) { datBusy = false; busyTicks = 0; }
    if (prgWaits && delays % 4 == 0) cardStatus = 0x900;  // TRAN|READY_FOR_DATA
  }
  unsigned busyTicks = 0;
  void enableHostMode() {}
};

#endif
