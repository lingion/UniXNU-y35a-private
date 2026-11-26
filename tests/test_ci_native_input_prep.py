from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/ci"))
import prepare_native_inputs


class TemporaryXnuHostToolPatchTest(unittest.TestCase):
    def test_restores_source_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "xnu"
            host_tool = source / "bsd/kern/makekdebugevents.py"
            host_tool.parent.mkdir(parents=True)
            host_tool.write_bytes(b"original")

            def apply_patch(_command, **_kwargs):
                host_tool.write_bytes(b"patched")

            with mock.patch.object(prepare_native_inputs, "run", side_effect=apply_patch):
                with prepare_native_inputs.temporary_xnu_host_tool_patch(source, Path("patch.py")):
                    self.assertEqual(host_tool.read_bytes(), b"patched")

            self.assertEqual(host_tool.read_bytes(), b"original")

    def test_restores_source_after_install_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "xnu"
            host_tool = source / "bsd/kern/makekdebugevents.py"
            host_tool.parent.mkdir(parents=True)
            host_tool.write_bytes(b"original")

            def apply_patch(_command, **_kwargs):
                host_tool.write_bytes(b"patched")

            with mock.patch.object(prepare_native_inputs, "run", side_effect=apply_patch):
                with self.assertRaisesRegex(RuntimeError, "header install failed"):
                    with prepare_native_inputs.temporary_xnu_host_tool_patch(source, Path("patch.py")):
                        raise RuntimeError("header install failed")

            self.assertEqual(host_tool.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
