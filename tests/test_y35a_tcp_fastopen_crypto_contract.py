import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-tcp-fastopen-r138.patch"


class Y35ATcpFastOpenCryptoContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_patch_changes_only_the_tcp_fastopen_owner(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/netinet/tcp_subr.c"])

    def test_y35a_fastopen_is_disabled_and_read_only_without_provider(self):
        self.assertIn("CTLFLAG_RD | CTLFLAG_LOCKED", self.patch)
        self.assertIn("tcp_fastopen, 0,", self.patch)
        self.assertIn(
            " int, tcp_fastopen, TCP_FASTOPEN_CLIENT | TCP_FASTOPEN_SERVER,",
            self.patch,
        )

    def test_tcp_init_skips_aes_key_setup_when_fastopen_is_disabled(self):
        self.assertRegex(
            self.added,
            r"if\s*\(tcp_fastopen\s*!=\s*0\s*&&\s*"
            r"ccaes_cbc_encrypt_mode\(\)\s*!=\s*NULL\)\s*\{"
            r"\s*tcp_tfo_init\(\);",
        )

    def test_fastopen_key_update_fails_closed_without_crypto_provider(self):
        self.assertRegex(
            self.added,
            r"if\s*\(ccaes_cbc_encrypt_mode\(\)\s*==\s*NULL\)\s*\{"
            r"\s*return\s+EOPNOTSUPP;",
        )


if __name__ == "__main__":
    unittest.main()
