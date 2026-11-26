#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "native_crypto.h"

/* Exercise exact write boundaries under ASan/UBSan, independently of QEMU's
 * instruction-result oracle. Include an unaligned saved-state byte buffer. */
int main(void)
{
    const uint32_t ops[]={0x5e000000,0x5e001000,0x5e002000,0x5e003000,
        0x5e004000,0x5e005000,0x5e006000,0x5e280800,0x5e281800,0x5e282800,
        0x4e284800,0x4e285800,0x4e286800,0x4e287800,0x0ee0e000,0x4ee0e000};
    uint64_t seed=0x123456789abcdefULL;
    for (unsigned int t=0;t<32000;t++) {
        uint8_t storage[514],before[514];
        for (unsigned int i=0;i<514;i++) {
            seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;storage[i]=(uint8_t)seed;
        }
        memcpy(before,storage,sizeof(storage));
        unsigned int op=t%16,rd=(unsigned int)seed&31,rn=(unsigned int)(seed>>5)&31,rm=(unsigned int)(seed>>10)&31;
        uint32_t instruction=ops[op]|rd|(rn<<5)|((op<7||op>13)?rm<<16:0);
        assert(native_crypto_emulate(instruction,storage+1)==1);
        for (unsigned int i=0;i<514;i++) if(i<1+rd*16||i>=1+(rd+1)*16) assert(storage[i]==before[i]);
        memcpy(before,storage,sizeof(storage));
        assert(native_crypto_emulate(0xd503201f,storage+1)==0);
        assert(memcmp(storage,before,sizeof(storage))==0);
    }
    puts("PASS 32000 sanitizer register-boundary cases");
}
