// Compile-only ABI evidence. This object is not added to the driver archive.
#include <IOKit/IOCPU.h>
#include <IOKit/IOPlatformExpert.h>
#include <machine/machine_routines.h>
#include <libkern/version.h>

static_assert(VERSION_MAJOR == 18 && VERSION_MINOR == 7, "wrong Darwin headers");
// These were measured in the legacy 4903 build. Recheck under the explicit
// Y35A profile instead of assuming that changing board macros preserves ABI.
static_assert(sizeof(IOCPU) == 184, "IOCPU layout changed");
static_assert(sizeof(IODTPlatformExpert) == 240, "IODTPlatformExpert layout changed");
static_assert(sizeof(ml_processor_info_t) == 144, "processor registration layout changed");
static_assert(__builtin_offsetof(ml_processor_info_t, cpu_id) == 0 &&
    __builtin_offsetof(ml_processor_info_t, phys_id) == 104 &&
    __builtin_offsetof(ml_processor_info_t, log_id) == 108 &&
    __builtin_offsetof(ml_processor_info_t, cluster_id) == 116 &&
    __builtin_offsetof(ml_processor_info_t, cluster_type) == 120,
    "processor registration offsets changed");
static_assert(__is_same(decltype(&ml_get_boot_cluster), cluster_type_t (*)(void)),
    "wrong 4903 boot cluster helper");
static_assert(__is_same(decltype(&ml_get_cpu_number), int (*)(uint32_t)),
    "wrong physical to logical CPU helper");
static_assert(__is_same(IOInterruptHandler, void (*)(void *, void *, void *, int)),
    "wrong interrupt callback ABI");
static_assert(__is_same(ipi_handler_t, void (*)(void)), "wrong IPI callback ABI");
static_assert(__is_same(time_base_enable_t, void (*)(cpu_id_t, boolean_t)),
    "wrong timebase callback ABI");
static_assert(__is_same(decltype(&ml_install_interrupt_handler),
    void (*)(void *, int, void *, IOInterruptHandler, void *)),
    "wrong interrupt installation ABI");
static_assert(__is_same(decltype(&IOCPU::enableCPUTimeBase), void (IOCPU::*)(bool)),
    "wrong IOCPU timebase method ABI");
static_assert(__is_same(decltype(&ml_processor_register),
    kern_return_t (*)(ml_processor_info_t *, processor_t *, ipi_handler_t *,
                     perfmon_interrupt_handler_func *)),
    "wrong CPU registration signature");

// Eight little-endian u64 values, decoded in abi-probe-layout.log.
extern "C" const unsigned long arm_driver_4903_abi[] = {
    sizeof(IOCPU), sizeof(IODTPlatformExpert), sizeof(ml_processor_info_t),
    __builtin_offsetof(ml_processor_info_t, cpu_id),
    __builtin_offsetof(ml_processor_info_t, phys_id),
    __builtin_offsetof(ml_processor_info_t, log_id),
    __builtin_offsetof(ml_processor_info_t, cluster_id),
    __builtin_offsetof(ml_processor_info_t, cluster_type)
};
