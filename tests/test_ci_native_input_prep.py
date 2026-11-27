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

    def test_firehose_1477_atomic_compat_header_is_generated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            libdispatch = root / "libdispatch"
            libplatform = root / "libplatform"
            fakeroot = root / "fakeroot"
            source = libdispatch / "src/firehose/firehose_buffer.c"
            source.parent.mkdir(parents=True)
            source.write_text("#include <os/atomic_private.h>\n")
            (libdispatch / "os").mkdir(parents=True)
            (libdispatch / "os/firehose_buffer_private.h").write_text("header\n")
            (libplatform / "private/os/internal").mkdir(parents=True)
            (libplatform / "private/os/internal/atomic.h").write_text("atomic\n")
            (libplatform / "private/os/lock_private.h").write_text("lock\n")
            with mock.patch.object(prepare_native_inputs, "preprocess_dispatch_headers", return_value=[]), \
                    mock.patch.object(prepare_native_inputs, "run"):
                prepare_native_inputs.build_firehose(
                    root / "xnu", libdispatch, libplatform, fakeroot, "clang")
            header = fakeroot / "usr/local/include/kernel/os/atomic_private.h"
            self.assertIn("#include <internal/atomic.h>", header.read_text())

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
