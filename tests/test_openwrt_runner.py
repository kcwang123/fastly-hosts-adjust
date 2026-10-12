import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

root = Path(__file__).resolve().parents[1] / "openwrt"
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("runner", root / "runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from settings import Settings


class RunnerTests(unittest.TestCase):
    def test_new_install_blocks_benchmark_until_implemented(self):
        with tempfile.TemporaryDirectory() as d:
            result = runner.run_once(Settings(retry_count=0), Path(d)/"state.json", Path(d)/"scan.json", 100000, executor=lambda *a, **k: Mock(returncode=2))
            self.assertEqual(result["status"], "pending")
            self.assertFalse((Path(d)/"state.json").exists())

    def test_health_runs_only_after_benchmark_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            state, scan = Path(d)/"state.json", Path(d)/"scan.json"
            state.write_text(json.dumps({"last_benchmark_epoch": 100000, "last_health_epoch": 80000}))
            def execute(cmd, **kwargs):
                scan.write_text(json.dumps({"safe_to_apply": False, "evidence": "latency_only",
                                            "candidates": [{"ip": "151.101.1.133"}]}))
                return Mock(returncode=0)
            result = runner.run_once(Settings(), state, scan, 100000, executor=execute)
            self.assertEqual(result, {"status": "ok", "mode": "health", "candidates": 1})
            self.assertEqual(runner.read_state(state)["last_health_epoch"], 100000)
            self.assertEqual(runner.choose_mode(Settings(), runner.read_state(state), 100001), "skip")

    def test_failure_does_not_advance_state(self):
        with tempfile.TemporaryDirectory() as d:
            state, scan = Path(d)/"state.json", Path(d)/"scan.json"
            state.write_text(json.dumps({"last_benchmark_epoch": 100000, "last_health_epoch": 1}))
            opts = Settings(retry_count=0)
            result = runner.run_once(opts, state, scan, 100000, executor=lambda *a, **k: Mock(returncode=2))
            self.assertEqual(result["status"], "error")
            self.assertEqual(runner.read_state(state)["last_health_epoch"], 1)


if __name__ == "__main__":
    unittest.main()
