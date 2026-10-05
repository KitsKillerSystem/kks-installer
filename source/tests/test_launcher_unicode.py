"""Regression: Cyrillic package names must not crash a redirected Windows EXE."""
import io,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import launcher

class LauncherUnicodeTests(unittest.TestCase):
    def test_package_check_on_cp1252_stdout_keeps_utf8_report(self):
        release=SimpleNamespace(name="KKS 1.1.0 Русский Français ✓",manifest_digest="a"*64,
                                data={"supported_build":"Steam 25636769"},files=dict.fromkeys(range(6)))
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/"report.json"
            raw=io.BytesIO();out=io.TextIOWrapper(raw,encoding="cp1252",errors="strict")
            with patch.object(sys,"argv",["launcher","--verify-package","--package","candidate.zip","--report",str(report)]),patch.object(sys,"stdout",out),patch.object(launcher,"import_package",return_value=release):
                self.assertEqual(launcher.main(),0)
            out.flush()
            result=json.loads(raw.getvalue().decode("ascii"))
            self.assertEqual(result["content"],release.name)
            self.assertEqual(json.loads(report.read_bytes()),result)
            self.assertIn("Русский",report.read_text("utf8"))
