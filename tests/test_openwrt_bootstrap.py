import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("runner_bootstrap",root/"runner.py")
runner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=runner;spec.loader.exec_module(runner)
from settings import Settings
SCAN={"schema_version":1,"safe_to_apply":False,"evidence":"latency_only",
      "candidates":[{"service":"github","ip":"151.101.1.133","latency_ms":10}]}
class BootstrapTests(unittest.TestCase):
    def test_first_health_then_due_benchmark(self):
        cfg=Settings(auto_benchmark=True,trusted_baselines={"raw.githubusercontent.com":"151.101.2.133"},retry_count=0)
        self.assertEqual(runner.choose_mode(cfg,{},100000),"health")
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json"; scan=Path(d)/"scan.json"
            def exec_scan(cmd,**kw):
                scan.write_text(json.dumps(SCAN))
                return Mock(returncode=0)
            outcome=runner.run_once(cfg,state,scan,100000,executor=exec_scan,config_path="config.json")
            self.assertEqual(outcome["mode"],"health")
            self.assertEqual(runner.choose_mode(cfg,runner.read_state(state),100001),"benchmark")
    def test_failed_health_never_enables_benchmark(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Settings(auto_benchmark=True,trusted_baselines={"raw.githubusercontent.com":"151.101.2.133"},retry_count=0)
            state=Path(d)/"state.json";scan=Path(d)/"scan.json"
            scan.write_text(json.dumps(SCAN))
            result=runner.run_once(cfg,state,scan,100000,executor=lambda *a,**kw:Mock(returncode=1),config_path="c")
            self.assertEqual(result["status"],"error")
            self.assertFalse(scan.exists())
            self.assertFalse(state.exists())
if __name__=="__main__":unittest.main()
