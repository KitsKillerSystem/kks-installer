"""Keep the shipped legacy restoration descriptor tied to the released bytes."""

import hashlib
from pathlib import Path
import unittest

from kks_installer import _legacy
from kks_installer.managed_engine import LegacyDescriptor
from kks_installer.platforms import SafetyError


class ReleaseContractTests(unittest.TestCase):
    def test_legacy_descriptor_is_byte_exact_released_manifest(self):
        original = Path(__file__).resolve().parents[1] / "release" / "manifest.json"
        self.assertEqual(_legacy.MANIFEST_BYTES, original.read_bytes())
        self.assertEqual(
            hashlib.sha256(_legacy.MANIFEST_BYTES).hexdigest(),
            "dda35c73a9c1119010a3a7c2d15517df2457b231d894e2b910dd34f1d5afd3e7",
        )
        self.assertEqual(_legacy.MANIFEST_SHA256, hashlib.sha256(original.read_bytes()).hexdigest())

    def test_shipped_legacy_descriptor_is_restore_only(self):
        descriptor = LegacyDescriptor()
        with self.assertRaises(SafetyError):
            descriptor.verify_payloads()
        with self.assertRaises(SafetyError):
            descriptor.payload("payload/interface/fonts_en.swf", "0" * 64)


if __name__ == "__main__":
    unittest.main()
