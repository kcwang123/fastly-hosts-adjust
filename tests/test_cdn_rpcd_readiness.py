import importlib.util
from pathlib import Path
import subprocess
import unittest

spec = importlib.util.spec_from_file_location("cdn_ready", Path(__file__).resolve().parents[1] / "tools" / "cdn_rpcd_readiness.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

GOOD_METHODS = """'cdn-optimizer' @ab123\n        "status":{}\n"""
GOOD_STATUS = '{"schema_version":1,"status":"not_tested","safe_to_apply":false}'

class ReadinessTests(unittest.TestCase):
    def test_immediate_ready(self):
        self.assertEqual(mod.poll(lambda: (GOOD_METHODS, GOOD_STATUS), sleep=lambda _: None), 1)

    def test_delayed_registration(self):
        calls = [0]
        def probe():
            calls[0] += 1
            if calls[0] < 3:
                raise subprocess.CalledProcessError(1, "ssh")
            return GOOD_METHODS, GOOD_STATUS
        self.assertEqual(mod.poll(probe, attempts=4, interval=0, sleep=lambda _: None), 3)

    def test_timeout_bounded(self):
        calls = [0]
        def probe():
            calls[0] += 1
            raise OSError("not found")
        with self.assertRaisesRegex(RuntimeError, "READINESS_TIMEOUT attempts=3"):
            mod.poll(probe, attempts=3, interval=0, sleep=lambda _: None)
        self.assertEqual(calls[0], 3)

    def test_no_scan_and_failclosed(self):
        for methods, status in (
            (GOOD_METHODS + ' "scan":{}', GOOD_STATUS),
            (GOOD_METHODS.replace('"status":{}', '"status":{ "x":"y" }'), GOOD_STATUS),
            (GOOD_METHODS.replace('@ab123', '@INVALID'), GOOD_STATUS),
            (GOOD_METHODS, GOOD_STATUS.replace('"safe_to_apply":false', '"safe_to_apply":false,"extra":1')),
            (GOOD_METHODS, GOOD_STATUS.replace('"safe_to_apply":false', '"safe_to_apply":false,"safe_to_apply":false')),
            (GOOD_METHODS, GOOD_STATUS.replace('"schema_version":1', '"schema_version":true')),
            (GOOD_METHODS, '{"schema_version":1,"status":"ok","safe_to_apply":true}'),
            (GOOD_METHODS, '{"schema_version":1,"status":"not_tested","safe_to_apply":false'),
        ):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    mod.validate(methods, status)

    def test_reject_unbounded(self):
        for attempts, interval in ((0, 2), (31, 2), (2, -1), (2, 11)):
            with self.assertRaises(ValueError):
                mod.poll(lambda: (GOOD_METHODS, GOOD_STATUS), attempts, interval)

if __name__ == "__main__":
    unittest.main()
