#!/usr/bin/env python3
"""Compare scalar crypto instruction semantics with QEMU's ARMv8 execution."""
import argparse
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--baseline',action='store_true')
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False); out=a.output.resolve()
if a.baseline:
    (out/'native_crypto.h').write_text('#include <stdint.h>\nstatic int native_crypto_emulate(uint32_t i, void *r) {(void)i;(void)r;return 0;}\n')
else:
    # Extract the actual source patch, not a second implementation in the test.
    subprocess.run(['git','apply','--unsafe-paths','--include=*native_crypto.h','--directory='+str(out),str(ROOT/'patches/xnu/native-crypto-instructions.patch')],cwd='/tmp',check=True)
    (out/'native_crypto.h').symlink_to(out/'osfmk/arm64/native_crypto.h')
ops=[('sha1c',0x5e000000),('sha1p',0x5e001000),('sha1m',0x5e002000),
     ('sha1su0',0x5e003000),('sha256h',0x5e004000),('sha256h2',0x5e005000),('sha256su1',0x5e006000),
     ('sha1h',0x5e280800),('sha1su1',0x5e281800),('sha256su0',0x5e282800),
     ('aese',0x4e284800),('aesd',0x4e285800),('aesmc',0x4e286800),('aesimc',0x4e287800),
     ('pmull',0x0ee0e000),('pmull2',0x4ee0e000)]
variants=[(0,1,2),(0,0,2),(0,1,0),(0,1,1),(31,31,31),(29,30,31)]
asm=['.arch armv8-a+crypto','.text','.global _start','_start:','msr daifset,#15','ldr x0,=0x48000000','mov sp,x0',
     'mov x0,#0x300000','msr cpacr_el1,x0','isb','bl test_main','b .']
entries=[]
for op,base in ops:
    for d,n,m in variants:
        two=op in ('sha1h','sha1su1','sha256su0','aese','aesd','aesmc','aesimc')
        word=base|d|(n<<5)|(0 if two else m<<16)
        name=f'oracle_{len(entries)}'; entries.append((name,word,op))
        asm += ['.global '+name,name+':','sub sp,sp,#64']
        asm += [f'stp d{i},d{i+1},[sp,#{(i-8)*8}]' for i in range(8,16,2)]
        asm += [f'ldp q{i},q{i+1},[x0,#{i*16}]' for i in range(0,32,2)]
        asm += [f'.inst {word:#x}']
        asm += [f'stp q{i},q{i+1},[x0,#{i*16}]' for i in range(0,32,2)]
        asm += [f'ldp d{i},d{i+1},[sp,#{(i-8)*8}]' for i in range(8,16,2)]
        asm += ['add sp,sp,#64','ret']
(out/'oracle.S').write_text('\n'.join(asm)+'\n')
c='''#include <stdint.h>
#include "native_crypto.h"
static void put(const char *s) {while(*s) *(volatile unsigned int *)0x09000000=(unsigned int)*s++;}
static void hex(unsigned int x) {for(int i=28;i>=0;i-=4) {char b[2]={"0123456789abcdef"[(x>>i)&15],0};put(b);}}
static void finish(unsigned int status) {uint64_t b[2]={0x20026,status};register uint64_t x0 __asm__("x0")=0x20;register void *x1 __asm__("x1")=b;__asm__ volatile("hlt #0xf000" : : "r"(x0),"r"(x1):"memory");for(;;);}
static uint64_t seed=0x123456789abcdefULL;
static uint64_t random_word(void) {seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;return seed;}
'''
c+='\n'.join('extern void '+n+'(void *);' for n,_,_ in entries)
c+='\nstruct entry {void (*run)(void *);uint32_t word;const char *name;};\nstatic const struct entry cases[]={\n'
c+='\n'.join('{'+n+','+hex(w)+',"'+op+'"},' for n,w,op in entries)+'};\n'
c+='''void test_main(void) {
    uint64_t actual[64],expected[64];unsigned int count=0;
    for(unsigned int c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        for(unsigned int t=0;t<256;t++) {
            for(unsigned int j=0;j<64;j++) actual[j]=expected[j]= t==0 ? 0 : t==1 ? ~(uint64_t)0 : random_word();
            cases[c].run(expected);
            if(!native_crypto_emulate(cases[c].word,actual)) {put("UNHANDLED ");put(cases[c].name);put("\\n");finish(1);}
            for(unsigned int j=0;j<64;j++) if(actual[j]!=expected[j]) {put("MISMATCH ");put(cases[c].name);put(" word=");hex(cases[c].word);put(" test=");hex(t);put(" lane=");hex(j);put("\\n");finish(2);}
            count++;
        }
    }
    const uint32_t invalid[]={0,0xffffffff,0xd503201f,0x5e007000,0x5e280c00,0x0e20e000,0x4e280800};
    for(unsigned int i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++) {
        for(unsigned int j=0;j<64;j++) actual[j]=expected[j]=random_word();
        if(native_crypto_emulate(invalid[i],actual)) {put("ACCEPTED UNKNOWN\\n");finish(3);}
        for(unsigned int j=0;j<64;j++) if(actual[j]!=expected[j]) {put("UNKNOWN MUTATED STATE\\n");finish(4);}
    }
    put("PASS crypto instruction comparisons=");hex(count);put("\\n");finish(0);
}
'''
(out/'test.c').write_text(c)
command=['/usr/bin/clang','--target=aarch64-none-elf','-march=armv8-a+crypto','-O2','-ffreestanding','-fno-builtin','-mgeneral-regs-only','-nostdlib','-fuse-ld=lld','-Wl,-Ttext=0x40080000','-Wl,-e,_start','-I'+str(out),str(out/'test.c'),str(out/'oracle.S'),'-o',str(out/'test.elf')]
subprocess.run(command,check=True)
run=subprocess.run(['qemu-system-aarch64','-M','virt,secure=off,virtualization=off','-cpu','cortex-a53','-m','512','-nographic','-monitor','none','-nic','none','-semihosting','-kernel',str(out/'test.elf')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40)
(out/'result.log').write_text(run.stdout);print(run.stdout);run.check_returncode()
assert 'PASS crypto' in run.stdout
