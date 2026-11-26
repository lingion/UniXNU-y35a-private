#!/usr/bin/env python3
"""Build a RAM-only eMMC read probe for the measured LK2nd Y35A handoff.

Requires warm-reset PMIC settings. The probe resumes RCA 2, reads EXT_CSD and
the first 34 user-area sectors, and resets. It never writes or erases storage.
"""
from pathlib import Path
import argparse, hashlib, json, struct, subprocess
from package_native import android_container, select_device_dt, align

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True,type=Path)
    p.add_argument('--stock-boot',required=True,type=Path)
    a=p.parse_args(); a.directory.mkdir(parents=True,exist_ok=False)
    src=Path(__file__).resolve().parent
    entry='''.section .text.entry
.global _start
_start:
 b enter
 .word 0
 .quad 0x80000
 .quad image_end-_start
 .quad 0,0,0,0
 .word 0x644d5241,0
enter:
 msr daifset,#15
 mrs x9,sctlr_el1
 tbnz x9,#0,halt
 ldr x9,=0x859d0000
 mov sp,x9
 bl probe_main
halt:
 wfe
 b halt
 .ltorg
'''
    (a.directory/'entry.S').write_text(entry)
    (a.directory/'layout.ld').write_text('ENTRY(_start)\nSECTIONS { . = 0x80080000; .text : { *(.text.entry) *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } image_end = .; /DISCARD/ : { *(.comment) *(.eh_frame*) } }\n')
    subprocess.run(['/usr/bin/clang++','--target=aarch64-none-elf','-O2','-nostdlib','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-builtin','-mgeneral-regs-only','-fuse-ld=lld','-Wl,-T,layout.ld','entry.S',str(src/'emmc_probe.cpp'),'-o','probe.elf'],cwd=a.directory,check=True)
    subprocess.run(['/usr/bin/llvm-objcopy','-O','binary','probe.elf','probe.bin'],cwd=a.directory,check=True)
    stock=a.stock_boot.read_bytes();v=struct.unpack_from('<10I',stock,8);page=v[7]
    off=page+align(v[0],page)+align(v[2],page)+align(v[4],page)
    image=android_container((a.directory/'probe.bin').read_bytes(),select_device_dt(stock[off:off+v[8]]))
    (a.directory/'emmc-probe-not-xnu.img').write_bytes(image)
    record=dict(purpose='RAM-only eMMC handoff characterization; not XNU',image_sha256=hashlib.sha256(image).hexdigest(),ext_csd_offset=1024,sectors_offset=2048,sectors_count=34,sector_bytes=512)
    (a.directory/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
