// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "emmc_pio.h"
#include <assert.h>
#include <stdio.h>
#include <vector>
struct Model {
  uint8_t ext[512] = {};
  uint32_t status = 0, argument = 0, offset = 0;
  unsigned delays = 0, fault = 0;
  bool powered = true, active = false, busy = false;
  std::vector<unsigned> commands;
  Model() { ext[213] = 0x20; }
  uint32_t read32(unsigned r) {
    if (r == 0x30) return status;
    if (r == 0x24) return busy ? 3 : active ? 1U << 11 : 0;
    if (r == 0x10) return 0x900;
    if (r == 0x20) {
      assert(active && offset < 512);
      uint32_t value = 0;
      for (unsigned b = 0; b < 4; ++b)
        value |= uint32_t(commands.back() == 8 ? ext[offset+b] : uint8_t(argument+offset+b)) << (8*b);
      offset += 4;
      if (offset == 512) { status |= 2; active = false; }
      return value;
    }
    return 0;
  }
  uint16_t read16(unsigned) { return powered ? 7 : 0; }
  uint8_t read8(unsigned) { return powered ? 0xb : 0; }
  void write32(unsigned r, uint32_t v) {
    if (r == 0x30) status &= ~v;
    if (r == 0x08) argument = v;
  }
  void write16(unsigned r, uint16_t v) {
    if (r != 0xe) return;
    unsigned cmd = v >> 8;
    assert(cmd == 5 || cmd == 7 || cmd == 8 || cmd == 17);
    commands.push_back(cmd); offset = 0;
    active = cmd == 8 || cmd == 17;
    status = fault == 1 ? 0x208000 : fault == 2 ? 0 : 1 | (active ? 0x20 : 0);
  }
  void write8(unsigned, uint8_t) {}
  void delay() { ++delays; }
  void enableHostMode() {}
};
int main() {
  uint8_t ext[512], block[512];
  {
    Model io; EmmcPio<Model> card(io);
    assert(card.resume(2, ext) && card.sectors() == 8192);
    assert(card.read(1, block));
    for (unsigned i=0;i<512;i++) assert(block[i] == uint8_t(i+1));
    size_t count=io.commands.size();
    assert(!card.read(8192, block) && !card.read(0, nullptr));
    assert(io.commands.size()==count);
  }
  for (unsigned part=1;part<8;part++) {
    Model io; io.ext[179]=part; EmmcPio<Model> card(io);
    assert(!card.resume(2, ext) && card.error==8);
    size_t count=io.commands.size(); assert(!card.read(0,block)); assert(count==io.commands.size());
  }
  {
    Model io; io.powered=false; EmmcPio<Model> card(io);
    assert(!card.resume(2,ext) && io.commands.empty() && card.error==7);
  }
  {
    Model io; io.busy=true; EmmcPio<Model> card(io);
    assert(!card.resume(2,ext) && io.commands.empty() && io.delays==50000 && card.error==3);
  }
  for(unsigned fault=1;fault<=2;fault++) {
    Model io; io.fault=fault; EmmcPio<Model> card(io);
    assert(!card.resume(2,ext) && io.commands.size()==1);
    assert(card.error==(fault==1 ? 2 : 1));
    assert(io.delays==(fault==1 ? 0 : 50000));
  }
  {
    Model io; EmmcPio<Model> card(io); assert(card.resume(2,ext));
    io.fault=1; assert(!card.read(0,block));
    size_t count=io.commands.size(); io.fault=0;
    assert(!card.read(0,block) && count==io.commands.size());
  }
  puts("eMMC PIO: data, bounds, partition isolation, timeout, error and fail-closed tests passed");
}
