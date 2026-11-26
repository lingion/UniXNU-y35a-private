import json
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-amfi-syscall-errno-r154.patch"
R150_PATCH = ROOT / "patches/xnu/native-y35a-platform-fallback-root-r150.patch"
READBACK = ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r152-secure-root-global-fallback-20261115/readback-r152-probe/readback.json"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo"
RUNNER = ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r154-v3-amfi-syscall-errno-20261115/device-sequence-r154.py"


class Y35AAmfiSyscallErrnoR154Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PATCH.is_file():
            raise AssertionError(f"R154 diagnostic patch is missing: {PATCH}")
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        spec = importlib.util.spec_from_file_location("r154_runner_contract", RUNNER)
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def test_patch_touches_only_mac_syscall_dispatcher(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, ["security/mac_base.c"])

    def test_patch_applies_cleanly_to_pinned_xnu_source(self):
        result = subprocess.run(
            ["git", "-C", str(SOURCE), "apply", "--check", str(PATCH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_observation_is_scoped_to_exact_policy_and_call(self):
        self.assertRegex(self.added, r'uap->call\s*==\s*90')
        self.assertRegex(self.added, r'strcmp\(target,\s*"AMFI"\)\s*==\s*0')

    def test_dispatch_state_instrumentation_is_y35a_only(self):
        guard = r"#if defined\(XNU_Y35A_A53\) && XNU_Y35A_A53"
        self.assertGreaterEqual(len(re.findall(guard, self.patch)), 6)
        self.assertRegex(self.patch, guard + r"\s*\n\+\s*int policy_found = 0;")
        self.assertRegex(self.patch, guard + r"[\s\S]*?policy_found = 1;[\s\S]*?#endif")
        self.assertRegex(self.patch, guard + r"[\s\S]*?handler_found = 1;[\s\S]*?#endif")

    def test_record_commits_full_errno_after_dispatch_state(self):
        self.assertRegex(
            self.added,
            r"\(\(uint64_t\)\(uint32_t\)error\s*<<\s*32\)",
        )
        self.assertIn("policy_found != 0) << 32", self.added)
        self.assertIn("handler_found != 0) << 33", self.added)
        self.assertIn("native_phase_marker_external(21, amfi_state);", self.added)
        self.assertIn("native_phase_marker_external(22, amfi_probe);", self.added)
        self.assertIn("0x34353152ULL", self.added)
        # Slot 22 is the commit word: full 32-bit errno plus exact R154 tag.
        encoded = (103 << 32) | int.from_bytes(b"R154", "little")
        self.assertEqual(encoded & 0xFFFFFFFF, int.from_bytes(b"R154", "little"))
        self.assertEqual((encoded >> 32) & 0xFFFFFFFF, 103)
        self.assertLess(self.added.index("native_phase_marker_external(21, amfi_state)"),
                        self.added.index("native_phase_marker_external(22, amfi_probe)"))

    def test_errno_decode_distinguishes_missing_policy_from_callback(self):
        tag = int.from_bytes(b"R154", "little")
        missing_state = self.runner.decode_r154_state(tag)
        errno_commit = self.runner.decode_r154_amfi_probe((103 << 32) | tag)
        missing = self.runner.r154_amfi_outcome("R150PSOK", "R150MROK", missing_state, errno_commit)
        self.assertTrue(missing["fresh"])
        self.assertEqual(missing["interpretation"], "ENOPOLICY; no matching AMFI policy name was found")

        named_no_callback = self.runner.decode_r154_state((1 << 32) | tag)
        absent_callback = self.runner.r154_amfi_outcome("R150PSOK", "R150MROK", named_no_callback, errno_commit)
        self.assertEqual(absent_callback["interpretation"], "ENOPOLICY; a named AMFI policy exists without a syscall callback")

        callback_state = self.runner.decode_r154_state((1 << 32) | (1 << 33) | tag)
        callback_error = self.runner.r154_amfi_outcome("R150PSOK", "R150MROK", callback_state, errno_commit)
        self.assertEqual(callback_error["interpretation"], "ENOPOLICY returned by the matched AMFI callback")

    def test_old_r150_carriers_do_not_look_like_fresh_r154_records(self):
        state = self.runner.decode_r154_state(int.from_bytes(b"R150PSOK", "little"))
        commit = self.runner.decode_r154_amfi_probe(int.from_bytes(b"R150MROK", "little"))
        result = self.runner.r154_amfi_outcome("R154STAT", "R154ERR", state, commit)
        self.assertFalse(result["fresh"])

    def test_observation_follows_policy_dispatch_and_preserves_return_value(self):
        self.assertIn("error = mpc->mpc_ops->mpo_policy_syscall", self.patch)
        self.assertLess(self.patch.index("R154AMFI"), self.patch.index("return error;"))
        self.assertIn("return error;", self.patch)
        self.assertNotRegex(self.added, r'\breturn\s+0\s*;')
        self.assertNotIn("mac_policy_register(", self.added)

    def test_slot_22_is_transferred_after_earlier_mountroot_marker(self):
        prior = R150_PATCH.read_text()
        self.assertIn("native_phase_marker_external(22, 0x4B4F524D30353152ULL); /* R150MROK */", prior)
        self.assertIn("native_phase_marker_external(23, 0x4B4F565230353152ULL); /* R150RVOK */", prior)
        self.assertIn("slot22 contains `R150MROK` in both baseline and final", (ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r152-secure-root-global-fallback-20261115/record-r152-v1.md").read_text())

    def test_readback_maps_slot_22_inside_captured_early_record(self):
        manifest = json.loads(READBACK.read_text())
        record = next(r for r in manifest["records"] if r["name"] == "early-fault-record")
        self.assertEqual(record["offset"] + 22 * 8, 0xF0)
        self.assertGreaterEqual(record["size"], (22 + 1) * 8)


if __name__ == "__main__":
    unittest.main()
