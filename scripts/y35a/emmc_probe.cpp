// SPDX-License-Identifier: BSD-2-Clause-Patent
// RAM-only hardware characterization. No XNU and no persistent media writes.
#include "emmc_pio.h"
struct Hardware {
  static constexpr uintptr_t base = 0x07824900;
  uint32_t read32(unsigned r) { return *(volatile uint32_t *)(base+r); }
  uint16_t read16(unsigned r) { return *(volatile uint16_t *)(base+r); }
  uint8_t read8(unsigned r) { return *(volatile uint8_t *)(base+r); }
  void barrier() { asm volatile("dsb sy" ::: "memory"); }
  void write32(unsigned r,uint32_t v) { *(volatile uint32_t *)(base+r)=v;barrier(); }
  void write16(unsigned r,uint16_t v) { *(volatile uint16_t *)(base+r)=v;barrier(); }
  void write8(unsigned r,uint8_t v) { *(volatile uint8_t *)(base+r)=v;barrier(); }
  void delay() {
    uint64_t start, now; asm volatile("mrs %0,cntpct_el0":"=r"(start));
    do { asm volatile("mrs %0,cntpct_el0":"=r"(now)); } while (now-start<192);
  }
  void enableHostMode() {
    // Enabling HC mode clears power, SDCLK and DLL state on this controller.
    // Preserve the measured loader configuration before crossing that boundary.
    uint8_t host=read8(0x28), power=read8(0x29);
    uint16_t clock=read16(0x2c), host2=read16(0x3e);
    uint32_t dll=read32(0x100), vendor=read32(0x10c), dll2=read32(0x1b4);
    *(volatile uint32_t *)0x07824078 |= 1;barrier();
    write32(0x38,0);
    write16(0x2c,clock & ~4U);
    write32(0x10c,vendor);
    write8(0x28,host);write16(0x3e,host2);
    write32(0x1b4,dll2);write32(0x100,dll);
    write8(0x29,power);
    // Match LK2nd's power-event acknowledgement; regulators remain configured.
    uint32_t pending=*(volatile uint32_t *)0x078240dc;
    *(volatile uint32_t *)0x078240e4=pending;
    uint32_t ack=*(volatile uint32_t *)0x078240e8;
    if(pending & 3) ack|=1;
    if(pending & 12) ack|=4;
    *(volatile uint32_t *)0x078240e8=ack;barrier();
    for(unsigned i=0;i<50000 && !(read16(0x2c)&2);i++) delay();
    write16(0x2c,clock);
  }
};
extern "C" void probe_main() {
  volatile uint32_t *report=(volatile uint32_t *)0x859e0000;
  for(unsigned i=0;i<0x11000/4;i++) report[i]=0;
  *(volatile uint64_t *)report=0x31434d4d41353359ULL; // Y35AMMC1
  Hardware io;
  const unsigned offsets[]={0x24,0x28,0x2c,0x30,0x34,0x38,0x40,0x44,0xfc,0x100,0x108};
  for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++) report[16+i]=io.read32(offsets[i]);
  report[30]=*(volatile uint32_t *)0x07824078;
  EmmcPio<Hardware> card(io);
  report[2]=1;
  if(card.resume(2,(uint8_t *)0x859e0400)) {
    report[2]=2;report[6]=card.sectors();
    for(unsigned sector=0;sector<34;sector++) {
      if(!card.read(sector,(uint8_t *)(uintptr_t)(0x859e0800+512*sector))) break;
      report[7]=sector+1;
    }
    if(report[7]==34) report[2]=3;
  }
  report[3]=card.error;report[4]=card.lastCommand;report[5]=card.status;report[8]=card.response;
  for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++) report[32+i]=io.read32(offsets[i]);
  asm volatile("dsb sy" ::: "memory");
  *(volatile uint32_t *)0x0860065c=0;
  asm volatile("dsb sy" ::: "memory");
  *(volatile uint32_t *)0x004ab000=0;
  asm volatile("dsb sy" ::: "memory");
  for(;;) asm volatile("wfe");
}
