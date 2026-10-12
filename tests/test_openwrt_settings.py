import importlib.util
import json
import pathlib
import tempfile
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "openwrt" / "settings.py"
spec = importlib.util.spec_from_file_location("settings", path)
mod = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class SettingsTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            file = pathlib.Path(d) / "config.json"
            file.write_text(json.dumps(data), encoding="utf-8")
            return mod.Settings.load(file)

    def test_defaults_and_due(self):
        s = self.load({})
        self.assertTrue(s.dry_run)
        self.assertEqual(s.due(100000)["benchmark"], True)
        self.assertEqual(s.due(100000, 99999, 99999), {"health": False, "benchmark": False})
        self.assertEqual(s.due(100000, 100000-10800, 100000-86400), {"health": True, "benchmark": True})

    def test_custom_intervals(self):
        s = self.load({"health_interval_hours": 6, "benchmark_interval_hours": 48})
        self.assertFalse(s.due(100000, 80000, 90000)["health"])
        self.assertTrue(s.due(100000, 78000, 90000)["health"])

    def test_reject_bad_settings(self):
        for data in ({"health_interval_hours": 0}, {"health_interval_hours": "3"},
                     {"benchmark_interval_hours": 2}, {"dry_run": "false"},
                     {"unsupported": 2}, {"process_timeout_seconds": 2000},
                     {"enabled_services": ["github", "github"]}, {"retry_count": -1}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)


if __name__ == "__main__":
    unittest.main()
