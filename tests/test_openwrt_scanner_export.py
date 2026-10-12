import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import Mock

root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scanner_export", root / "openwrt" / "scanner_export.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ScannerExportTests(unittest.TestCase):
    def test_schema_never_authorizes_dns_write(self):
        upstream = Mock()
        upstream.BUILTIN = [{"key": "github"}, {"key": "twitch"}]
        upstream.scan_keys.return_value = ["github"]
        upstream.scan.return_value = {
            "scanned": 5, "skipped": 3,
            "found": {"github": [{"ip": "151.101.1.133", "pop": "TPE", "latency_ms": 11.55}]}
        }
        result = mod.run_scan(upstream, ["github"], 5)
        self.assertFalse(result["safe_to_apply"])
        self.assertEqual(result["evidence"], "latency_only")
        self.assertEqual(result["candidates"][0]["latency_ms"], 11.55)

    def test_empty_scan(self):
        upstream = Mock()
        upstream.BUILTIN = [{"key": "github"}]
        upstream.scan_keys.return_value = ["github"]
        upstream.scan.return_value = {"scanned": 2, "skipped": 2, "found": {"github": []}}
        self.assertEqual(mod.run_scan(upstream, ["github"], 5)["candidates"], [])


if __name__ == "__main__":
    unittest.main()
