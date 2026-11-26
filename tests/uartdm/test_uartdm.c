/* Host fake-MMIO contract for the exact production UARTDM leaf. */
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

static uint32_t sr, isr, dmen;
static unsigned reads, writes, sr_delay, tx_ready_delay, ready_after_count;
static struct { unsigned offset; uint32_t value; } log_writes[32];
static uint32_t fake_read(uintptr_t base, unsigned offset)
{
    assert(base == 0x12340000);
    ++reads;
    if (offset == 0xa4) {
        if (sr_delay) { --sr_delay; return 0; }
        if (tx_ready_delay) { --tx_ready_delay; return sr & ~4u; }
        if (ready_after_count && !writes) return sr & ~4u;
        return sr;
    }
    if (offset == 0xb4) return isr;
    if (offset == 0x3c) return dmen;
    assert(!"unexpected register read (legacy DM/GENI/PL011?)");
    return 0;
}
static void fake_write(uintptr_t base, unsigned offset, uint32_t value)
{
    assert(base == 0x12340000 && writes < 32);
    log_writes[writes].offset = offset;
    log_writes[writes++].value = value;
}
#define UARTDM_READ32 fake_read
#define UARTDM_WRITE32 fake_write
#include <pexpert/arm/uartdm.h>

static void reset(void)
{
    sr = 0xc; isr = dmen = reads = writes = sr_delay = tx_ready_delay = ready_after_count = 0;
    memset(log_writes, 0, sizeof(log_writes));
}
static void compatible_contract(void)
{
    const char list[] = "vivo,uart\0qcom,msm-uartdm-v1.4";
    assert(uartdm_compatible(list, sizeof(list)));
    assert(uartdm_compatible("qcom,msm-uartdm-v1.4", 21));
    assert(!uartdm_compatible("qcom,msm-uartdm-v1.4", 20));
    assert(!uartdm_compatible("qcom,msm-uartdm-v1.3", 21));
    assert(!uartdm_compatible("qcom,geni-uart", 15));
    assert(!uartdm_compatible("arm,pl011", 10));
    assert(!uartdm_compatible("qcom,msm-uartdm-v1.4x", 22));
    assert(!uartdm_compatible(NULL, 0));
}
static void word_and_count_contract(void)
{
    const uint8_t bytes[] = {0x00, 0x81, 0xfe, 0xff};
    for (unsigned count = 1; count <= 4; ++count) {
        reset();
        assert(uartdm_write_word(0x12340000, bytes, count, 8));
        assert(writes == 3);
        assert(log_writes[0].offset == 0x40 && log_writes[0].value == count);
        assert(log_writes[1].offset == 0xa8 && log_writes[1].value == 0x300);
        assert(log_writes[2].offset == 0x100);
        uint32_t expected = 0;
        for (unsigned i = 0; i < count; ++i) expected |= (uint32_t)bytes[i] << (8 * i);
        assert(log_writes[2].value == expected);
    }
    reset();
    assert(!uartdm_write_word(0x12340000, bytes, 0, 8));
    assert(!uartdm_write_word(0x12340000, bytes, 5, 8));
    assert(!uartdm_write_word(0x12340000, NULL, 1, 8));
    assert(!uartdm_write_word(0x12340000, bytes, 1, 0));
    assert(!reads && !writes);
}
static void ready_and_timeout_contract(void)
{
    const uint8_t byte = '\n';
    reset(); ready_after_count = 1; /* Follow LK: NCF_TX/reset before polling TXRDY. */
    assert(uartdm_write_word(0x12340000, &byte, 1, 8));
    reset(); sr_delay = 3;
    assert(uartdm_write_word(0x12340000, &byte, 1, 8));
    assert(log_writes[2].value == '\n'); /* serial_console owns CRLF policy. */
    reset(); sr = 4; isr = 0x80; /* TX_READY, even without SR_TXEMT. */
    assert(uartdm_write_word(0x12340000, &byte, 1, 8));
    reset(); tx_ready_delay = 3;
    assert(uartdm_write_word(0x12340000, &byte, 1, 8));
    reset(); sr = 0;
    assert(!uartdm_write_word(0x12340000, &byte, 1, 8));
    assert(!writes && reads <= 25);
    reset(); sr = 8; /* Drain complete but FIFO never becomes writable. */
    assert(!uartdm_write_word(0x12340000, &byte, 1, 8));
    assert(writes == 2 && reads <= 25); /* Count/command only; never write FIFO. */
    reset(); dmen = 1;
    assert(!uartdm_write_word(0x12340000, &byte, 1, 8));
    assert(!writes);
    reset();
    assert(!uartdm_drain(0x12340000, 0));
    assert(!reads && !writes);
    assert(uartdm_drain(0x12340000, 8));
    reset(); sr = 4;
    assert(!uartdm_drain(0x12340000, 8));
    assert(reads == 8 && !writes);
}
static void rx_availability_contract(void)
{
    reset(); sr = 0;
    assert(!uartdm_rx_available(0x12340000));
    sr = 1; assert(uartdm_rx_available(0x12340000));
    sr = 0x10; assert(!uartdm_rx_available(0x12340000));
    assert(reads == 3 && !writes); /* Never consume FIFO or clear status. */
}
int main(void)
{
    compatible_contract(); word_and_count_contract();
    ready_and_timeout_contract(); rx_availability_contract();
    puts("PASS: UARTDM compatible, FIFO readiness, packing/count, bounded drain, RXRDY");
    return 0;
}
