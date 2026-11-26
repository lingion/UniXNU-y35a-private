#!/usr/bin/env python3
"""Check the linked Y35A single-CPU PRNG registration order.

The gate establishes that the boot-thread registration call precedes every
direct read_random call, and that the linked provider uses XNU's HMAC-DRBG
factory. It does not establish entropy quality or cryptographic validation.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from verify_low_vector import MachO, signed


def direct_bl_targets(image: bytes, start: int, end: int) -> list[tuple[int, int]]:
    macho = MachO(image)
    if start >= end or start % 4 or end % 4:
        raise ValueError("function interval must be aligned and increasing")
    calls = []
    for pc in range(start, end, 4):
        word = macho.word(pc)
        if word & 0xFC000000 == 0x94000000:
            calls.append((pc, pc + 4 * signed(word & 0x03FFFFFF, 26)))
    return calls


def verify(image: bytes) -> dict:
    failures = []
    report = {"ok": False, "failures": failures}
    try:
        macho = MachO(image)
        symbols = macho.symbols
        required = ("_kernel_bootstrap", "_scale_setup", "_kernel_thread_create",
                    "_kernel_bootstrap_thread", "_load_context", "_idle_thread_create",
                    "_y35a_prng_bootstrap_init", "_register_and_init_prng",
                    "_read_random", "_ccdrbg_factory_nisthmac",
                    "_y35a_prng_registration_started", "_y35a_prng_initialized",
                    "_y35a_prng_lock_pointer", "_y35a_prng_bootstrap_entered",
                    "_y35a_prng_bootstrap_returned", "_y35a_bootstrap_phase",
                    "_y35a_cckprng_functions",
                    "_y35a_cckprng_init", "_y35a_cckprng_reseed",
                    "_y35a_cckprng_addentropy", "_y35a_cckprng_generate")
        missing = [name for name in required if name not in symbols]
        if missing:
            raise ValueError("missing linked PRNG integration symbols: " + ", ".join(missing))
        bootstrap_calls = direct_bl_targets(image, symbols["_kernel_bootstrap"],
                                            symbols["_scale_setup"])
        thread_create_calls = [pc for pc, target in bootstrap_calls
                               if target == symbols["_kernel_thread_create"]]
        thread_start, thread_end = symbols["_kernel_bootstrap_thread"], symbols["_load_context"]
        thread_calls = direct_bl_targets(image, thread_start, thread_end)
        init_calls = [pc for pc, target in thread_calls
                      if target == symbols["_y35a_prng_bootstrap_init"]]
        idle_calls = [pc for pc, target in thread_calls
                      if target == symbols["_idle_thread_create"]]
        read_calls = [pc for pc, target in thread_calls if target == symbols["_read_random"]]
        if len(init_calls) != 1:
            failures.append(f"expected one early PRNG registration call in kernel_bootstrap_thread, found {len(init_calls)}")
        if len(thread_create_calls) != 1:
            failures.append(f"expected one kernel_thread_create call in kernel_bootstrap, found {len(thread_create_calls)}")
        if len(idle_calls) != 1:
            failures.append(f"expected one idle_thread_create call in kernel_bootstrap_thread, found {len(idle_calls)}")
        if not read_calls:
            failures.append("no direct read_random consumer found in kernel_bootstrap_thread")
        if len(init_calls) == len(idle_calls) == 1 and init_calls[0] >= idle_calls[0]:
            failures.append("PRNG registration does not precede idle_thread_create")
        if len(init_calls) == 1 and read_calls and init_calls[0] >= min(read_calls):
            failures.append("PRNG registration does not precede the first read_random consumer")
        wrapper_start = symbols["_y35a_prng_bootstrap_init"]
        wrapper_end = min(wrapper_start + 0x100, symbols["_read_random"])
        wrapper_calls = direct_bl_targets(image, wrapper_start, wrapper_end)
        if not any(target == symbols["_register_and_init_prng"] for _, target in wrapper_calls):
            failures.append("Y35A bootstrap wrapper does not call register_and_init_prng")
        init_start, init_end = symbols["_y35a_cckprng_init"], symbols["_y35a_cckprng_reseed"]
        provider_calls = direct_bl_targets(image, init_start, init_end)
        if not any(target == symbols["_ccdrbg_factory_nisthmac"] for _, target in provider_calls):
            failures.append("Y35A PRNG provider does not initialize the linked HMAC-DRBG")
        callbacks = ("_y35a_cckprng_init", "_y35a_cckprng_reseed",
                     "_y35a_cckprng_addentropy", "_y35a_cckprng_generate")
        table = symbols["_y35a_cckprng_functions"]
        table_values = tuple(struct.unpack_from("<Q", image, macho.offset(table + i * 8))[0]
                             for i in range(len(callbacks)))
        expected_values = tuple(symbols[name] for name in callbacks)
        if table_values != expected_values:
            failures.append("linked CCKPRNG callback table does not match the validated provider functions")
        report.update(kernel_bootstrap=hex(symbols["_kernel_bootstrap"]),
                      kernel_bootstrap_thread=hex(thread_start),
                      registration_call_pcs=[hex(x) for x in init_calls],
                      kernel_thread_create_call_pcs=[hex(x) for x in thread_create_calls],
                      idle_thread_create_call_pcs=[hex(x) for x in idle_calls],
                      read_random_call_pcs=[hex(x) for x in read_calls],
                      hmac_drbg_factory=hex(symbols["_ccdrbg_factory_nisthmac"]),
                      provider_callbacks={name: hex(value) for name, value in zip(callbacks, table_values)},
                      initialized_witness=hex(symbols["_y35a_prng_initialized"]),
                      phase_witness=hex(symbols["_y35a_bootstrap_phase"]))
    except (KeyError, ValueError, struct.error) as error:
        failures.append(str(error))
    report["ok"] = not failures
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.kernel.read_bytes())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
