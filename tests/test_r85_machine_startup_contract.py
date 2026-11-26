import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
SPEC = importlib.util.spec_from_file_location(
    "verify_phase_instrumentation",
    ROOT / "scripts/y35a/verify_phase_instrumentation.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def marker(name, *, slot=None):
    expected_slot, value = MODULE.R85_ARM_INIT_MARKERS[name]
    slot = expected_slot if slot is None else slot
    return [
        f"mov x11, #{value & 0xffff:#x}",
        f"movk x11, #{(value >> 16) & 0xffff:#x}, lsl #16",
        f"movk x11, #{(value >> 32) & 0xffff:#x}, lsl #32",
        f"movk x11, #{(value >> 48) & 0xffff:#x}, lsl #48",
        f"str x11, [x19, #{0x800 + slot * 8:#x}]",
        "dc civac, x10",
        "dsb sy",
    ]


def phase_set(value):
    return [
        f"mov x0, #{value & 0xffff:#x}",
        f"movk x0, #{(value >> 16) & 0xffff:#x}, lsl #16",
        f"movk x0, #{(value >> 32) & 0xffff:#x}, lsl #32",
        f"movk x0, #{(value >> 48) & 0xffff:#x}, lsl #48",
        "bl _y35a_bootstrap_phase_set",
    ]


def valid_body():
    lines = marker("R84MST00")
    lines += phase_set(MODULE.R84_LATE_PHASE)
    lines += marker("R85LRET0")
    lines += marker("R85MSB00")
    lines += ["bl _machine_startup"]
    lines += marker("R85MACH0")
    return "\n".join(lines)


def external_marker_call(name):
    markers = (MODULE.R93_BSD_MARKERS if name in MODULE.R93_BSD_MARKERS else
               MODULE.R92_BSD_MARKERS if name in MODULE.R92_BSD_MARKERS else
               MODULE.R91_BSD_MARKERS if name in MODULE.R91_BSD_MARKERS else
               MODULE.R90_BSD_MARKERS if name in MODULE.R90_BSD_MARKERS else
               MODULE.R89_BSD_MARKERS if name in MODULE.R89_BSD_MARKERS else
               MODULE.R88_STARTUP_MARKERS if name in MODULE.R88_STARTUP_MARKERS else
               MODULE.R87_STARTUP_MARKERS if name in MODULE.R87_STARTUP_MARKERS else
               MODULE.R86_STARTUP_MARKERS)
    slot, value = markers[name]
    return [
        f"mov w0, #{slot:#x}",
        f"mov x1, #{value & 0xffff:#x}",
        f"movk x1, #{(value >> 16) & 0xffff:#x}, lsl #16",
        f"movk x1, #{(value >> 32) & 0xffff:#x}, lsl #32",
        f"movk x1, #{(value >> 48) & 0xffff:#x}, lsl #48",
        "bl _native_phase_marker_external",
    ]


def r86_disassembly():
    machine = ["_machine_startup:"] + external_marker_call("R86MSE00") + [
        "bl _y35a_bootstrap_phase_set", "bl _PE_parse_boot_argn",
    ]
    bootstrap = ["_kernel_bootstrap:"] + external_marker_call("R86KBE00") + [
        "bl _y35a_bootstrap_phase_set", "bl _vm_mem_bootstrap",
    ] + external_marker_call("R86VMB00") + [
        "bl _cs_init",
    ] + external_marker_call("R86CSI00") + [
        "bl _vm_mem_init",
    ] + external_marker_call("R86VMI00") + [
        "bl _console_init",
    ] + external_marker_call("R86CON00") + [
        "bl _sched_init",
    ] + external_marker_call("R86SCH00") + [
        "bl _ipc_init",
    ] + external_marker_call("R86IPC00")
    helper = [
        "_native_phase_marker_external:",
        "add x8, x8, w0, uxtw #3",
        "add x9, x8, #0x800",
        "str x1, [x8, #0x800]",
        "dc civac, x9",
        "dsb sy",
        "ret",
    ]
    return "\n".join(machine + bootstrap + helper)


def r87_disassembly():
    bootstrap = ["_kernel_bootstrap:"] + external_marker_call("R87PMAP0") + [
        "bl _mapping_free_prime",
    ] + external_marker_call("R87FREE0") + [
        "bl _machine_init",
    ] + external_marker_call("R87MACH0") + [
        "bl _clock_init",
    ] + external_marker_call("R87CLK00") + [
        "bl _task_init",
    ] + external_marker_call("R87TASK0") + [
        "bl _thread_init",
    ] + external_marker_call("R87THRD0") + [
        "bl _kernel_thread_create",
    ] + external_marker_call("R87KTC00")
    thread = ["_kernel_bootstrap_thread:"] + external_marker_call("R87KBT00") + [
        "bl _y35a_bootstrap_phase_set", "bl _current_processor",
    ] + external_marker_call("R87CPU00")
    helper = [
        "_native_phase_marker_external:",
        "add x8, x8, w0, uxtw #3",
        "add x9, x8, #0x800",
        "str x1, [x8, #0x800]",
        "dc civac, x9",
        "dsb sy",
        "ret",
    ]
    return "\n".join(bootstrap + thread + helper)


def r88_disassembly():
    thread = ["_kernel_bootstrap_thread:"] + external_marker_call("R88PRBEG") + [
        "bl _y35a_prng_bootstrap_init",
    ] + external_marker_call("R88PRNOK") + [
        "bl _idle_thread_create",
    ] + external_marker_call("R88IDLE0") + [
        "bl _sched_startup",
    ] + external_marker_call("R88SCHED") + [
        "bl _thread_daemon_init",
    ] + external_marker_call("R88DAEM0") + [
        "bl _thread_call_initialize",
    ] + external_marker_call("R88CALL0") + [
        "bl _thread_bind",
    ] + external_marker_call("R88BIND0") + [
        "bl _ipc_thread_call_init",
    ] + external_marker_call("R88IPCT0") + [
        "bl _mapping_adjust",
    ] + external_marker_call("R88MAP00") + [
        "bl _clock_service_create",
    ] + external_marker_call("R88CLK00") + [
        "bl _device_service_create",
    ] + external_marker_call("R88DEV00") + [
        "bl _bsd_early_init",
    ] + external_marker_call("R88BSDE0") + [
        "bl _ml_lockdown_init",
    ] + external_marker_call("R88LOCK0") + [
        "bl _PE_init_iokit",
    ] + external_marker_call("R88IOKIT") + [
        "bl _ml_set_interrupts_enabled",
    ] + external_marker_call("R88SPL00") + [
        "bl _vm_shared_region_init",
    ] + external_marker_call("R88SHR00") + external_marker_call("R88BSDC0") + [
        "bl _bsd_init",
    ] + external_marker_call("R88BSDRT")
    helper = [
        "_native_phase_marker_external:", "cmp w0, #47",
        "add x8, x8, w0, uxtw #3", "add x9, x8, #0x800",
        "str x1, [x8, #0x800]", "dc civac, x9", "dsb sy", "ret",
    ]
    return "\n".join(thread + helper)


def r89_disassembly():
    bsd = ["_bsd_init:"] + external_marker_call("R89BSDI0") + [
        "bl _throttle_init",
    ] + external_marker_call("R89THRTL") + [
        "bl _kmeminit",
    ] + external_marker_call("R89KMEM0") + [
        "bl _parse_bsd_args",
    ] + external_marker_call("R89ARGS0") + [
        "bl _kauth_init",
    ] + external_marker_call("R89KAUT0") + [
        "bl _procinit",
    ] + external_marker_call("R89PROC0") + [
        "bl _tty_init",
    ] + external_marker_call("R89TTY00") + external_marker_call("R89MNTC0") + [
        "bl _vfs_mountroot",
    ] + external_marker_call("R89MNTOK") + external_marker_call("R89MNTER") + [
        "bl _VFS_ROOT",
    ] + external_marker_call("R89ROOT0") + [
        "bl _devfs_kernel_mount",
    ] + external_marker_call("R89DEVF0") + [
        "bl _bsd_utaskbootstrap",
    ] + ["bl _cloneproc", "bl _proc_find", "bl _task_clear_return_wait"] + external_marker_call("R89UTBS0") + [
        "bl _init_system_override",
    ] + external_marker_call("R89BSRET")
    task = ["_bsdinit_task:", "bl _current_proc"] + external_marker_call("R89BTASK") + [
        "bl _vm_init_before_launchd",
    ] + external_marker_call("R89VMIL0") + external_marker_call("R89INIT0") + [
        "bl _load_init_program",
    ] + external_marker_call("R89LRET0")
    helper = [
        "_native_phase_marker_external:", "cmp w0, #47",
        "add x8, x8, w0, uxtw #3", "add x9, x8, #0x800",
        "str x1, [x8, #0x800]", "dc civac, x9", "dsb sy", "ret",
    ]
    return "\n".join(bsd + task + helper)


def r90_disassembly():
    bsd = ["_bsd_init:"] + external_marker_call("R89TTY00") + external_marker_call("R90PNAM0") + [
        "bl _file_lock_init",
    ] + external_marker_call("R90LOCK0") + [
        "bl _kmem_suballoc",
    ] + external_marker_call("R90SUBM0") + [
        "bl _fpxlog_init",
    ] + external_marker_call("R90FPX00") + [
        "bl _vnode_pager_bootstrap",
    ] + external_marker_call("R90VPG00") + [
        "bl _inittodr",
    ] + external_marker_call("R90TOD00") + external_marker_call("R90MNTC0") + [
        "bl _vfs_mountroot",
    ] + external_marker_call("R90MNTOK") + external_marker_call("R90MNTER") + [
        "bl _VFS_ROOT",
    ] + external_marker_call("R90ROOT0") + [
        "bl _devfs_kernel_mount",
    ] + external_marker_call("R90DEVF0") + [
        "bl _cloneproc", "bl _proc_find", "bl _task_clear_return_wait",
    ] + external_marker_call("R90UTBS0") + [
        "bl _init_system_override",
    ] + external_marker_call("R90BSRET")
    task = ["_bsdinit_task:", "bl _current_proc"] + external_marker_call("R90BTASK") + [
        "bl _vm_init_before_launchd",
    ] + external_marker_call("R90VMIL0") + external_marker_call("R90INIT0") + [
        "bl _load_init_program",
    ] + external_marker_call("R90LRET0")
    helper = [
        "_native_phase_marker_external:", "cmp w0, #47",
        "add x8, x8, w0, uxtw #3", "add x9, x8, #0x800",
        "str x1, [x8, #0x800]", "dc civac, x9", "dsb sy", "ret",
    ]
    return "\n".join(bsd + task + helper)


def r91_disassembly():
    bsd = ["_bsd_init:"] + external_marker_call("R90FPX00")
    bsd += external_marker_call("R91BBEG0") + ["bl _bsd_bufferinit"]
    bsd += external_marker_call("R91BEND0")
    for function, name in (
        ("IOKitInitializeTime", "R91TIME0"),
        ("ubc_init", "R91UBC00"),
        ("vfsinit", "R91VFS00"),
        ("proc_uuid_policy_init", "R91UUID0"),
        ("mbinit", "R91MBIN0"),
        ("pipeinit", "R91PIPE0"),
        ("pthread_init", "R91PTHR0"),
        ("select_waitq_init", "R91SLCT0"),
        ("domaininit", "R91DOMN0"),
        ("acct_init", "R91ACCT0"),
        ("bsd_autoconf", "R91AUTO0"),
        ("os_reason_init", "R91OSRS0"),
        ("mptcp_control_register", "R91NETDN"),
    ):
        bsd += [f"bl _{function}"] + external_marker_call(name)
    bsd += external_marker_call("R91VPPRE") + ["bl _vnode_pager_bootstrap"]
    bsd += external_marker_call("R91VPGOK") + ["bl _inittodr"]
    bsd += external_marker_call("R91TOD00") + ["bl _IOFindBSDRoot"]
    bsd += external_marker_call("R91CONF0") + external_marker_call("R91MNTC0")
    bsd += ["bl _vfs_mountroot"] + external_marker_call("R91MNTOK")
    bsd += external_marker_call("R91MNTER") + ["bl _VFS_ROOT"]
    bsd += external_marker_call("R91ROOT0") + ["bl _devfs_kernel_mount"]
    bsd += external_marker_call("R91DEVF0") + ["bl _bsd_utaskbootstrap"]
    bsd += external_marker_call("R91UTBS0") + ["bl _init_system_override"]
    bsd += external_marker_call("R91TAIL0")
    task = ["_bsdinit_task:", "bl _current_proc"] + external_marker_call("R91TASK0")
    task += ["bl _vm_init_before_launchd"] + external_marker_call("R91VMIL0")
    task += external_marker_call("R91INIT0") + ["bl _load_init_program"]
    task += external_marker_call("R91LRET0")
    helper = [
        "_native_phase_marker_external:", "cmp w0, #47",
        "add x8, x8, w0, uxtw #3", "add x9, x8, #0x800",
        "str x1, [x8, #0x800]", "dc civac, x9", "dsb sy", "ret",
    ]
    return "\n".join(bsd + task + helper)


def r92_disassembly():
    body = r91_disassembly()
    for function, before, after in (
        ("IOKitInitializeTime", "R92TPRE0", "R92TOK00"),
        ("ubc_init", "R92UPRE0", "R92UOK00"),
        ("vfsinit", "R92VPRE0", "R92VOK00"),
    ):
        before_lines = "\n".join(external_marker_call(before)) + "\n"
        after_lines = "\n" + "\n".join(external_marker_call(after))
        body = body.replace(f"bl _{function}", before_lines + f"bl _{function}" + after_lines, 1)
    return body


def r93_disassembly():
    body = r92_disassembly()
    function = [
        "_IOKitInitializeTime:",
        *external_marker_call("R93IENT0"),
        *external_marker_call("R93RPRE0"),
        "bl _IOService_resourceMatching",
        *external_marker_call("R93ROK00"),
        *external_marker_call("R93WPRE0"),
        "bl _IOService_waitForService",
        *external_marker_call("R93WOK00"),
        *external_marker_call("R93CPRE0"),
        "bl _clock_initialize_calendar",
        *external_marker_call("R93COK00"),
    ]
    return body.replace(
        "_bsdinit_task:", "\n".join(function) + "\n_bsdinit_task:"
    )


class R85MachineStartupContractTest(unittest.TestCase):
    def verify(self, body, *, required=True):
        with mock.patch.object(MODULE, "verify_r84_arm_init_progress", return_value=[]):
            return MODULE.verify_r85_machine_startup(body, required=required)

    def test_r85_requires_ordered_persistent_machine_startup_boundaries(self):
        self.assertEqual(self.verify(valid_body()), [])

    def test_r85_rejects_missing_machine_startup_call(self):
        body = valid_body().replace("bl _machine_startup\n", "")
        failures = self.verify(body)
        self.assertTrue(any("one machine_startup call" in item for item in failures))

    def test_r85_rejects_wrong_carrier_slot(self):
        body = valid_body().replace(
            f"str x11, [x19, #{0x800 + 12 * 8:#x}]",
            f"str x11, [x19, #{0x800 + 14 * 8:#x}]",
        )
        failures = self.verify(body)
        self.assertTrue(any("R85MSB00" in item and "slot12" in item for item in failures))

    def test_r85_rejects_unpersisted_marker(self):
        body = valid_body().replace(
            "str x11, [x19, #0x860]\ndc civac, x10\ndsb sy",
            "str x11, [x19, #0x860]\nnop\nnop",
            1,
        )
        failures = self.verify(body)
        self.assertTrue(any("R85MSB00" in item and "DC CIVAC" in item for item in failures))

    def test_r85_rejects_machine_startup_return_before_call(self):
        body = valid_body()
        return_marker = "\n".join(marker("R85MACH0"))
        body = body.replace("bl _machine_startup\n" + return_marker,
                            return_marker + "\nbl _machine_startup")
        failures = self.verify(body)
        self.assertTrue(any("out of order" in item for item in failures))

    def _decode_raw_pair(self, *, return_marker=False):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        slot11 = (MODULE.R85_MACHINE_RETURN_MARKER if return_marker
                  else MODULE.R85_LATE_RETURN_MARKER)
        after[early + 11 * 8:early + 12 * 8] = slot11.to_bytes(8, "little")
        after[early + 12 * 8:early + 13 * 8] = MODULE.R85_MACHINE_START_MARKER.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r84_entry_ladder", return_value={
            "markers": {"setter_return": {"status": "absent"}},
            "progress": "arm-init-machine-startup-boundary",
        }):
            return MODULE.decode_r85_machine_startup(final, manifest, baseline)

    def test_r85_callsite_marker_does_not_claim_function_entry(self):
        result = self._decode_raw_pair()
        self.assertTrue(result["machine_startup_callsite_reached"])
        self.assertFalse(result["machine_startup_entry_witnessed"])
        self.assertIsNone(result["machine_startup_entered"])
        self.assertFalse(result["machine_startup_returned"])
        self.assertEqual(result["progress"], "machine-startup-callsite-reached")

    def test_r85_return_marker_proves_function_entry_and_return(self):
        result = self._decode_raw_pair(return_marker=True)
        self.assertTrue(result["machine_startup_callsite_reached"])
        self.assertTrue(result["machine_startup_entry_witnessed"])
        self.assertTrue(result["machine_startup_entered"])
        self.assertTrue(result["machine_startup_returned"])
        self.assertEqual(result["progress"], "machine-startup-returned")

    def test_r86_static_gate_binds_entry_and_ordered_bootstrap_returns(self):
        self.assertEqual(MODULE.verify_r86_startup_disassembly(r86_disassembly()), [])

    def test_r86_static_gate_rejects_a_marker_before_its_stage_call_returns(self):
        body = r86_disassembly().replace(
            "bl _vm_mem_bootstrap\n" + "\n".join(external_marker_call("R86VMB00")),
            "\n".join(external_marker_call("R86VMB00")) + "\nbl _vm_mem_bootstrap",
        )
        failures = MODULE.verify_r86_startup_disassembly(body)
        self.assertTrue(any("R86VMB00 must follow vm_mem_bootstrap returning" in item
                            for item in failures))

    def test_r86_raw_decode_reports_highest_fresh_stage(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        for name in ("R86MSE00", "R86KBE00", "R86VMB00"):
            slot, value = MODULE.R86_STARTUP_MARKERS[name]
            after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r85_machine_startup", return_value={
            "markers": {}, "progress": "machine-startup-callsite-reached", "limitations": [],
        }):
            result = MODULE.decode_r86_startup(final, manifest, baseline)
        self.assertTrue(result["machine_startup_function_entry_witnessed"])
        self.assertTrue(result["kernel_bootstrap_entry_witnessed"])
        self.assertEqual(result["progress"], "R86VMB00")

    def test_r87_static_gate_binds_post_call_and_thread_entry_markers(self):
        self.assertEqual(MODULE.verify_r87_bootstrap_thread_disassembly(r87_disassembly()), [])

    def test_r87_static_gate_rejects_a_stage_marker_before_its_call(self):
        body = r87_disassembly().replace(
            "bl _task_init\n" + "\n".join(external_marker_call("R87TASK0")),
            "\n".join(external_marker_call("R87TASK0")) + "\nbl _task_init",
        )
        failures = MODULE.verify_r87_bootstrap_thread_disassembly(body)
        self.assertTrue(any("R87TASK0 must follow task_init returning" in item
                            for item in failures))

    def test_r87_raw_decode_reports_thread_entry_as_highest_stage(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        for name in ("R87PMAP0", "R87MACH0", "R87KBT00"):
            slot, value = MODULE.R87_STARTUP_MARKERS[name]
            after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r86_startup", return_value={
            "markers": {}, "progress": "R86IPC00", "limitations": [],
        }):
            result = MODULE.decode_r87_startup(final, manifest, baseline)
        self.assertTrue(result["machine_startup_function_entry_witnessed"])
        self.assertTrue(result["kernel_bootstrap_entry_witnessed"])
        self.assertTrue(result["kernel_bootstrap_thread_entry_witnessed"])
        self.assertFalse(result["current_processor_returned"])
        self.assertEqual(result["progress"], "R87KBT00")

    def test_r88_static_gate_binds_bsd_iokit_stages(self):
        self.assertEqual(MODULE.verify_r88_bsd_iokit_disassembly(r88_disassembly()), [])

    def test_r88_static_gate_rejects_marker_before_stage_call(self):
        body = r88_disassembly().replace(
            "bl _sched_startup\n" + "\n".join(external_marker_call("R88SCHED")),
            "\n".join(external_marker_call("R88SCHED")) + "\nbl _sched_startup",
        )
        failures = MODULE.verify_r88_bsd_iokit_disassembly(body)
        self.assertTrue(any("R88SCHED must follow sched_startup returning" in item
                            for item in failures))

    def _decode_r88_raw_markers(self, names):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        for name in names:
            slot, value = MODULE.R88_STARTUP_MARKERS[name]
            after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r87_startup", return_value={
            "markers": {}, "progress": "R87CPU00", "limitations": [],
        }):
            return MODULE.decode_r88_bsd_iokit(final, manifest, baseline)

    def test_r88_raw_decode_distinguishes_prng_entry_from_return(self):
        result = self._decode_r88_raw_markers(("R88PRBEG",))
        self.assertTrue(result["prng_bootstrap_entered"])
        self.assertFalse(result["prng_bootstrap_returned"])

    def test_r88_later_markers_prove_prng_return_and_reach_bsd_callsite(self):
        result = self._decode_r88_raw_markers(("R88PRNOK", "R88IDLE0", "R88BSDC0"))
        self.assertTrue(result["prng_bootstrap_entered"])
        self.assertTrue(result["prng_bootstrap_returned"])
        self.assertTrue(result["bsd_init_callsite_reached"])
        self.assertFalse(result["bsd_init_returned"])
        self.assertEqual(result["progress"], "R88BSDC0")

    def test_r89_static_gate_binds_bsd_root_and_init_program_order(self):
        self.assertEqual(MODULE.verify_r89_bsd_init_disassembly(r89_disassembly()), [])

    def test_r89_static_gate_rejects_mount_marker_before_mount_call(self):
        body = r89_disassembly().replace(
            "bl _vfs_mountroot\n" + "\n".join(external_marker_call("R89MNTOK")),
            "\n".join(external_marker_call("R89MNTOK")) + "\nbl _vfs_mountroot",
        )
        failures = MODULE.verify_r89_bsd_init_disassembly(body)
        self.assertTrue(any("R89MNTOK must follow vfs_mountroot returning" in item
                            for item in failures))

    def test_r89_raw_decode_reports_root_and_init_program_boundaries(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        for name in ("R89BSDI0", "R89MNTOK", "R89ROOT0", "R89UTBS0",
                     "R89BTASK", "R89VMIL0", "R89INIT0"):
            slot, value = MODULE.R89_BSD_MARKERS[name]
            after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r88_bsd_iokit", return_value={
            "r88_markers": {"R88BSDRT": {"fresh": False}},
            "progress": "R88BSDC0", "limitations": [],
        }):
            result = MODULE.decode_r89_bsd_init(final, manifest, baseline)
        self.assertTrue(result["machine_startup_function_entry_witnessed"])
        self.assertTrue(result["kernel_bootstrap_entry_witnessed"])
        self.assertTrue(result["kernel_bootstrap_thread_entry_witnessed"])
        self.assertTrue(result["bsd_init_entry_witnessed"])
        self.assertEqual(result["root_mount_result"], "mounted")
        self.assertTrue(result["bsd_utaskbootstrap_returned"])
        self.assertTrue(result["bsdinit_task_entry_witnessed"])
        self.assertTrue(result["bsd_init_returned"])
        self.assertTrue(result["init_program_callsite_reached"])
        self.assertFalse(result["load_init_program_returned"])
        self.assertEqual(result["progress"], "R89INIT0")

    def test_r90_static_gate_binds_pre_root_and_process_startup(self):
        self.assertEqual(MODULE.verify_r90_bsd_root_disassembly(r90_disassembly()), [])

    def test_r90_static_gate_rejects_mount_marker_before_call(self):
        body = r90_disassembly().replace(
            "bl _vfs_mountroot\n" + "\n".join(external_marker_call("R90MNTOK")),
            "\n".join(external_marker_call("R90MNTOK")) + "\nbl _vfs_mountroot",
        )
        failures = MODULE.verify_r90_bsd_root_disassembly(body)
        self.assertTrue(any("R90MNTOK must follow vfs_mountroot returning" in item
                            for item in failures))

    def test_r90_static_gate_rejects_duplicate_bsdinit_return_marker(self):
        body = r90_disassembly().replace(
            "_bsdinit_task:",
            "\n".join(external_marker_call("R90BSRET")) + "\n_bsdinit_task:",
        )
        failures = MODULE.verify_r90_bsd_root_disassembly(body)
        self.assertTrue(any("R90BSRET" in item and "found 2" in item
                            for item in failures))

    def test_r90_tail_cursor_does_not_claim_bsd_init_returned(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        slot, value = MODULE.R90_BSD_MARKERS["R90BSRET"]
        offset = MODULE.RAW_STAGE_BASE_OFFSET + slot * 8
        after[offset:offset + 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r89_bsd_init", return_value={
            "r88_markers": {"R88BSDRT": {"fresh": False}},
            "progress": "R89TTY00", "limitations": [],
        }):
            result = MODULE.decode_r90_bsd_root(final, manifest, baseline)
        self.assertTrue(result["bsd_init_tail_reached"])
        self.assertFalse(result["bsd_init_body_completed"])
        self.assertFalse(result["bsd_init_returned"])

    def test_r90_fresh_mount_error_is_not_inferred_as_mounted(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        for name in ("R90MNTC0", "R90MNTER"):
            slot, value = MODULE.R90_BSD_MARKERS[name]
            offset = MODULE.RAW_STAGE_BASE_OFFSET + slot * 8
            after[offset:offset + 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r89_bsd_init", return_value={
            "r88_markers": {"R88BSDRT": {"fresh": False}},
            "progress": "R89TTY00", "limitations": [],
        }):
            result = MODULE.decode_r90_bsd_root(final, manifest, baseline)
        self.assertEqual(result["root_mount_result"], "returned-error")
        self.assertTrue(result["root_mount_callsite_reached"])
        self.assertFalse(result["root_vnode_ready"])

    def test_r91_static_gate_binds_post_fpx_bsd_cursor_and_root_path(self):
        self.assertEqual(
            MODULE.verify_r91_bsd_cursor_disassembly(r91_disassembly()), []
        )

    def test_r91_static_gate_rejects_buffer_return_cursor_before_call(self):
        body = r91_disassembly().replace(
            "bl _bsd_bufferinit\n" + "\n".join(external_marker_call("R91BEND0")),
            "\n".join(external_marker_call("R91BEND0")) + "\nbl _bsd_bufferinit",
        )
        failures = MODULE.verify_r91_bsd_cursor_disassembly(body)
        self.assertTrue(any("R91BEND0 must follow bsd_bufferinit" in item
                            for item in failures))

    def test_r91_raw_decode_reports_latest_slot37_cursor(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        old_slot, old_value = MODULE.R89_BSD_MARKERS["R89TTY00"]
        before[early + old_slot * 8:early + (old_slot + 1) * 8] = old_value.to_bytes(8, "little")
        slot, value = MODULE.R91_BSD_MARKERS["R91VFS00"]
        after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r90_bsd_root", return_value={
            "r90_markers": {}, "progress": "R90FPX00", "limitations": [],
        }):
            result = MODULE.decode_r91_bsd_cursor(final, manifest, baseline)
        self.assertEqual(result["r91_progress"], "R91VFS00")
        self.assertTrue(result["r91_markers"]["R91VFS00"]["fresh"])
        self.assertEqual(result["r91_markers"]["R91BBEG0"]["status"], "superseded")
        self.assertTrue(result["r91_markers"]["R91BBEG0"]["reached_by_inference"])
        self.assertEqual(result["progress"], "R91VFS00")

    def test_marker_argument_decoder_tracks_callee_saved_orr_reuse(self):
        lines = [
            "mov x19, #0x3952",
            "movk x19, #0x5430, lsl #16",
            "movk x19, #0x444f, lsl #32",
            "movk x19, #0x3030, lsl #48",
            "mov w0, #43",
            "mov x1, x19",
            "bl _native_phase_marker_external",
            "orr x1, x19, #0x10000",
            "mov w0, #37",
            "bl _native_phase_marker_external",
        ]
        events = MODULE._marker_helper_calls("\n".join(lines))
        self.assertEqual(events[-1][1:], (
            37, int.from_bytes(b"R91TOD00", "little")
        ))

    def test_r92_static_gate_binds_pre_and_return_cursors(self):
        self.assertEqual(
            MODULE.verify_r92_bsd_disassembly(r92_disassembly()), []
        )

    def test_r92_static_gate_rejects_return_cursor_before_the_call(self):
        body = r92_disassembly().replace(
            "bl _IOKitInitializeTime\n" + "\n".join(external_marker_call("R92TOK00")),
            "\n".join(external_marker_call("R92TOK00")) + "\nbl _IOKitInitializeTime",
        )
        failures = MODULE.verify_r92_bsd_disassembly(body)
        self.assertTrue(any("R92TOK00 must follow IOKitInitializeTime" in item
                            for item in failures))

    def test_r92_raw_decode_distinguishes_callsite_from_return(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        slot, value = MODULE.R92_BSD_MARKERS["R92TPRE0"]
        offset = MODULE.RAW_STAGE_BASE_OFFSET + slot * 8
        after[offset:offset + 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r91_bsd_cursor", return_value={
            "progress": "R91BEND0", "r91_cursor": {"owner": "R91BEND0"},
            "r91_markers": {}, "limitations": [],
        }):
            result = MODULE.decode_r92_bsd_cursor(final, manifest, baseline)
        self.assertEqual(result["r92_progress"], "R92TPRE0")
        self.assertTrue(result["r92_markers"]["R92TPRE0"]["fresh"])
        self.assertFalse(result["r92_markers"]["R92TOK00"]["fresh"])
        self.assertEqual(result["r92_markers"]["R92TOK00"]["status"], "not-reached")

    def test_r93_static_gate_binds_iokit_resource_wait_and_clock_order(self):
        self.assertEqual(
            MODULE.verify_r93_iokit_time_disassembly(r93_disassembly()), []
        )

    def test_r93_static_gate_rejects_clock_return_cursor_before_call(self):
        body = r93_disassembly().replace(
            "bl _clock_initialize_calendar\n"
            + "\n".join(external_marker_call("R93COK00")),
            "\n".join(external_marker_call("R93COK00"))
            + "\nbl _clock_initialize_calendar",
        )
        failures = MODULE.verify_r93_iokit_time_disassembly(body)
        self.assertTrue(any("R93COK00 must follow clock_initialize_calendar" in item
                            for item in failures))

    def test_r93_raw_decode_distinguishes_wait_entry_from_return(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        slot, value = MODULE.R93_BSD_MARKERS["R93WPRE0"]
        offset = MODULE.RAW_STAGE_BASE_OFFSET + slot * 8
        after[offset:offset + 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r92_bsd_cursor", return_value={
            "progress": "R92TPRE0", "r92_cursor": {"owner": "R92TPRE0", "fresh": False},
            "r92_markers": {}, "limitations": [],
        }):
            result = MODULE.decode_r93_iokit_time(final, manifest, baseline)
        self.assertEqual(result["r93_progress"], "R93WPRE0")
        self.assertTrue(result["r93_markers"]["R93WPRE0"]["fresh"])
        self.assertEqual(result["r93_iokit_state"], "inside-waitForService")

    def test_r90_raw_decode_reports_mount_and_process_startup_boundaries(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "records": [{
                "name": "early-fault-record", "physical": "0xa000",
                "report_offset": 0, "size": MODULE.EARLY_RECORD_BYTES,
            }],
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + MODULE.EARLY_RECORD_BYTES
        before = bytearray(size)
        after = bytearray(size)
        early = MODULE.RAW_STAGE_BASE_OFFSET
        for name in ("R90PNAM0", "R90MNTOK", "R90ROOT0", "R90UTBS0",
                     "R90BTASK", "R90VMIL0", "R90INIT0"):
            slot, value = MODULE.R90_BSD_MARKERS[name]
            after[early + slot * 8:early + (slot + 1) * 8] = value.to_bytes(8, "little")
        baseline.write_bytes(before)
        final.write_bytes(after)
        with mock.patch.object(MODULE, "decode_r89_bsd_init", return_value={
            "r88_markers": {"R88BSDRT": {"fresh": False}},
            "progress": "R89TTY00", "limitations": [],
        }):
            result = MODULE.decode_r90_bsd_root(final, manifest, baseline)
        self.assertTrue(result["bsd_init_entry_witnessed"])
        self.assertEqual(result["root_mount_result"], "mounted")
        self.assertEqual(result["r90_markers"]["R90MNTOK"]["status"], "superseded")
        self.assertTrue(result["r90_markers"]["R90MNTOK"]["reached_by_inference"])
        self.assertTrue(result["root_vnode_ready"])
        self.assertTrue(result["bsd_utaskbootstrap_returned"])
        self.assertTrue(result["bsdinit_task_entry_witnessed"])
        self.assertTrue(result["init_program_callsite_reached"])
        self.assertEqual(result["progress"], "R90INIT0")


if __name__ == "__main__":
    unittest.main()
