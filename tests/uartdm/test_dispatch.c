/* Compile the real patched pe_serial.c, replacing only kernel/DT/MMIO services. */
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define MARK_AS_HIBERNATE_DATA
#define MARK_AS_HIBERNATE_TEXT
#define MARK_AS_HIBERNATE_DATA_CONST_LATE
#define SECURITY_READ_ONLY_LATE(x) x
#define HIBERNATION 0
#define VMAPPLE_UART 1
#define PRIVATE 1
#define THREAD_UNINT 0
#define THREAD_CONTINUE_NULL NULL
#define THREAD_AWAKENED 0
#define NSEC_PER_USEC 1000
#define KERN_FAILURE 1
#define KERN_SUCCESS 0
#define kSuccess 0
#define kError -1
typedef uintptr_t vm_offset_t;
typedef int kern_return_t;
typedef void *DTEntry;
#include <pexpert/arm/protos.h>
static uint32_t registers_[1024];
static uintptr_t region[] = {0x1000, 0x1000};
static uint32_t reg_bytes = sizeof(region);
static const char *compat = "qcom,msm-uartdm-v1.4";
static uint32_t compat_bytes = 21;
static unsigned maps, mmio_reads, mmio_writes;
static uintptr_t mapped_phys, mapped_size;
static bool marker = true, map_fail;
static vm_offset_t soc = 0x12000000;
static uint32_t __unused fake_read(uintptr_t base, unsigned offset)
{
    assert(base == (uintptr_t)registers_);
    assert(offset == 0xa4 || offset == 0xb4 || offset == 0x3c);
    ++mmio_reads;
    return registers_[offset / 4];
}
static void __unused fake_write(uintptr_t base, unsigned offset, uint32_t value)
{
    assert(base == (uintptr_t)registers_);
    assert(offset == 0x40 || offset == 0xa8 || offset == 0x100);
    ++mmio_writes;
    registers_[offset / 4] = value;
}
#define UARTDM_READ32 fake_read
#define UARTDM_WRITE32 fake_write
vm_offset_t pe_arm_get_soc_base_phys(void) { return soc; }
static vm_offset_t ml_io_map(vm_offset_t phys, uintptr_t size)
{
    ++maps; mapped_phys = phys; mapped_size = size;
    return map_fail ? 0 : (uintptr_t)registers_;
}
static int SecureDTFindEntry(const char *name, const char *value, DTEntry *entry)
{
    if ((!strcmp(name, "boot-console") && marker) ||
        (!strcmp(name, "name") && !strcmp(value, "uart0"))) {
        *entry = registers_; return kSuccess;
    }
    return kError;
}
static int SecureDTGetProperty(DTEntry entry, const char *name, const void **value, uint32_t *size)
{
    assert(entry == registers_);
    if (!strcmp(name, "reg")) { *value = region; *size = reg_bytes; return kSuccess; }
    if (!strcmp(name, "compatible") && compat) {
        *value = compat; *size = compat_bytes; return kSuccess;
    }
    return kError;
}
static void PE_parse_boot_argn(const char *n __unused, void *v __unused, unsigned s __unused) {}
static void nanoseconds_to_absolutetime(uint64_t n, uint64_t *r) { *r = n; }
static uint64_t mach_absolute_time(void) { return 0; }
static void assert_wait_deadline(void *p __unused, int a __unused, uint64_t d __unused) {}
static void thread_block(void *p __unused) { assert(!"UARTDM must never block"); }
static void *current_thread(void) { return NULL; }
static void clear_wait(void *p __unused, int s __unused) {}
static void thread_wakeup(void *p __unused) {}
#include "pe_serial_host.c"

static void reset(void)
{
    gPESF = NULL; uart_initted = false; serial_do_transmit = true;
#if XNU_NATIVE_UARTDM
    uartdm_base = 0;
#endif
    maps = mmio_reads = mmio_writes = 0; map_fail = false; marker = true;
    soc = 0x12000000; region[0] = region[1] = 0x1000;
    reg_bytes = sizeof(region); compat = "qcom,msm-uartdm-v1.4"; compat_bytes = 21;
    memset(registers_, 0, sizeof(registers_));
    registers_[0xa4 / 4] = 0xc;
    vmapple_uart0_base_vaddr = 0;
}
int main(void)
{
    reset();
#if XNU_NATIVE_UARTDM
    assert(serial_init());
    assert(gPESF && gPESF->device == SERIAL_UARTDM && !gPESF->has_irq && !gPESF->next);
    assert(maps == 1 && mapped_phys == 0x12001000 && mapped_size == 0x1000);
    assert(!mmio_reads && !mmio_writes); /* No clock/GPIO/mode programming at init. */
    uart_putc('A');
    assert(mmio_writes == 3 && registers_[0x100 / 4] == 'A' && registers_[0x40 / 4] == 1);
    registers_[0xa4 / 4] = 1;
    unsigned previous_reads = mmio_reads;
    assert(uart_getc() == -1 && previous_reads == mmio_reads);
    mmio_reads = 0; uart_putc('B'); /* Stuck FIFO must not trap generic outer poll. */
    assert(mmio_reads <= 300001 && mmio_writes == 3);
    serial_go_to_sleep(); /* Drain also bounded when TX never empties. */
    assert(mmio_reads <= 400001);
    assert(serial_init() && maps == 1); /* No-op reinit, no new mapping. */
    assert(serial_irq_enable(SERIAL_UARTDM) == KERN_FAILURE);
    assert(!serial_irq_filter(SERIAL_UARTDM));
    reset(); marker = false; assert(serial_init() && gPESF->device == SERIAL_UARTDM);
    reset(); reg_bytes = 8; assert(!serial_init() && !maps && !mmio_writes);
    reset(); region[1] = 0x100; assert(!serial_init() && !maps);
    reset(); region[0] = 1; assert(!serial_init() && !maps);
    reset(); region[0] = UINTPTR_MAX - 0xfff; assert(!serial_init() && !maps);
    reset(); map_fail = true; assert(!serial_init() && maps == 1 && !mmio_writes);
    reset(); soc = 0; region[0] = 0x078b0000; region[1] = 0x200;
    assert(serial_init() && gPESF->device == SERIAL_UARTDM);
    assert(maps == 1 && mapped_phys == 0x078b0000 && mapped_size == 0x200);
    reset(); compat_bytes = 20; assert(serial_init() && gPESF->device == SERIAL_VMAPPLE_UART);
    reset(); compat = "arm,pl011"; compat_bytes = 10;
    assert(serial_init() && gPESF->device == SERIAL_VMAPPLE_UART);
    assert(registers_[0x30 / 4] == 0x301 && !mmio_writes);
#else
    assert(serial_init() && gPESF->device == SERIAL_VMAPPLE_UART);
    assert(registers_[0x30 / 4] == 0x301 && !mmio_reads && !mmio_writes);
#endif
    puts("PASS: real serial_init/uart_putc dispatch, DT mapping, bounds, native guard, PL011 preservation");
    return 0;
}
