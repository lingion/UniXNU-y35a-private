"""Contract tests for the Y35A APFS root-selection verifier."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_root_selection_contract",
    ROOT / "scripts/y35a/verify_root_selection_contract.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def make_gpt_image(path: Path, volume_uuid: str) -> None:
    header = bytearray(512)
    header[:8] = b"EFI PART"
    struct.pack_into("<I", header, 80, 128)
    struct.pack_into("<I", header, 84, 2)
    import uuid
    entry = bytearray(128)
    entry[:16] = uuid.UUID(MODULE.GPT_HINT_UUID).bytes_le
    entry[16:32] = uuid.UUID(volume_uuid).bytes_le
    struct.pack_into("<QQ", entry, 32, 409640, 9155151)
    entry[56:56 + len("disk image") * 2] = "disk image".encode("utf-16-le")
    path.write_bytes(bytes(512) + bytes(header) + bytes(entry) + bytes(128))


def make_boot3(path: Path, command: str) -> None:
    image = bytearray(0x2000)
    image[:8] = b"ANDROID!"
    image[MODULE.BOOT_LINE_OFFSET:MODULE.BOOT_LINE_OFFSET + len(command)] = command.encode()
    path.write_bytes(image)


def make_raw(path: Path, kernel: Path, logs: bytes) -> None:
    blob = bytearray(0x11000)
    prefix = bytes.fromhex(hashlib.sha256(kernel.read_bytes()).hexdigest()[:16])
    blob[:8] = b"Y35ARD01"
    blob[8:16] = prefix
    blob[0x10000:0x10008] = b"Y35ARD01"
    blob[0x10040:0x10048 + len(logs)] = logs
    path.write_bytes(blob)


class RootSelectionContractTest(unittest.TestCase):
    def fixture(self) -> dict:
        return {
            "kernel_sha256": "0aa286cbfb1da9a8b5ac02dd06e840db3bad1333664991ad46cc0f7b17f56545",
            "boot-uuid": MODULE.ROOT_UUID,
            "rd": "uuid",
            "osenvironment": "default",
        }

    def test_boot_line_finder_reads_shim_embedded_boot_args(self):
        image = bytearray(0x2000)
        command = b"-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid=" + MODULE.ROOT_UUID.encode()
        image[0xBE0:0xBE0 + len(command)] = command
        self.assertEqual(MODULE.boot_line(bytes(image)), command)

    def test_rd_uuid_without_boot_uuid_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"kernel")
            apfs = root / "os.dmg"
            make_gpt_image(apfs, MODULE.ROOT_UUID)
            iokit = root / "IOKitBSDInit.cpp"
            iokit.write_text('getProperty( "boot-uuid" ); strncmp( look, "uuid", strlen( "uuid" )) == 0; '
                             '"rd=uuid but no boot-uuid=<value> specified"; '
                             'IOService::publishResource( "boot-uuid", uuidString ); '
                             'return IOService::resourceMatching( "boot-uuid-media" ); '
                             'OSString::withCStringNoCopy("Apple_HFS");')
            boot3 = root / "boot3.img"
            make_boot3(boot3, "-v serial=3 cpus=1 debug=0x8 rd=uuid")
            raw = root / "final.raw"
            make_raw(raw, kernel, b"rooting via boot-uuid\nWaiting for boot volume with UUID\nBSD root: disk0s2")
            image = MODULE.verify([str(boot3), str(kernel), str(raw), str(apfs), str(iokit)])
            self.assertIn("boot-uuid is ''", " ".join(image["failures"]))

    def test_valid_uuid_boot_line_and_fresh_log_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"kernel")
            apfs = root / "os.dmg"
            make_gpt_image(apfs, MODULE.ROOT_UUID)
            iokit = root / "IOKitBSDInit.cpp"
            iokit.write_text('getProperty( "boot-uuid" ); strncmp( look, "uuid", strlen( "uuid" )) == 0; '
                             '"rd=uuid but no boot-uuid=<value> specified"; '
                             'IOService::publishResource( "boot-uuid", uuidString ); '
                             'return IOService::resourceMatching( "boot-uuid-media" ); '
                             'OSString::withCStringNoCopy("Apple_HFS");')
            boot3 = root / "boot3.img"
            make_boot3(boot3, "-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid=" + MODULE.ROOT_UUID)
            raw = root / "final.raw"
            make_raw(raw, kernel, b"rooting via boot-uuid\nWaiting for boot volume with UUID\nBSD root: disk0s2")
            image = MODULE.verify([str(boot3), str(kernel), str(raw), str(apfs), str(iokit)])
            self.assertEqual(image["status"], "PASS", image["failures"])

    def test_raw_without_fresh_root_log_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"kernel")
            apfs = root / "os.dmg"
            make_gpt_image(apfs, MODULE.ROOT_UUID)
            iokit = root / "IOKitBSDInit.cpp"
            iokit.write_text('getProperty( "boot-uuid" ); strncmp( look, "uuid", strlen( "uuid" )) == 0; '
                             '"rd=uuid but no boot-uuid=<value> specified"; '
                             'IOService::publishResource( "boot-uuid", uuidString ); '
                             'return IOService::resourceMatching( "boot-uuid-media" ); '
                             'OSString::withCStringNoCopy("Apple_HFS");')
            boot3 = root / "boot3.img"
            make_boot3(boot3, "-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid=" + MODULE.ROOT_UUID)
            raw = root / "final.raw"
            make_raw(raw, kernel, b"")
            image = MODULE.verify([str(boot3), str(kernel), str(raw), str(apfs), str(iokit)])
            self.assertTrue(any("no fresh boot-uuid root-selection log" in failure
                                for failure in image["failures"]), image["failures"])


if __name__ == "__main__":
    unittest.main()
