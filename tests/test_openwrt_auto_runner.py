import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("runner_auto",root/"runner.py")
runner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=runner;spec.loader.exec_module(runner)
from settings import Settings
SCAN={"schema_version":1,"evidence":"latency_only","safe_to_apply":False,
      "candidates":[{"service":"github","ip":"151.101.1.133","latency_ms":9}]}
PIN={"raw.githubusercontent.com":"151.101.2.133"}
class AutoRunnerTests(unittest.TestCase):
    def config(self):
        return Settings(auto_benchmark=True,trusted_baselines=PIN)
    def test_auto_refuses_stale_scan_before_api(self):
        with tempfile.TemporaryDirectory() as d:
            scan=Path(d)/"scan.json";scan.write_text(json.dumps(SCAN))
            os.utime(scan,(time.time()-20000,time.time()-20000))
            with self.assertRaisesRegex(ValueError,"stale"):
                runner.benchmark_due_with_config(self.config(),{},scan,100,"config.json",
                    lambda *a,**k:self.fail("no network"))
    def test_auto_blocks_rewritten_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            scan=Path(d)/"scan.json";scan.write_text(json.dumps(SCAN))
            class API:
                def __init__(self,*a):pass
                def list(self):return [{"domain":"raw.githubusercontent.com","answer":"151.101.2.133"}]
            with patch.dict(os.environ,{"ADGUARD_USER":"fake","ADGUARD_PASSWORD":"fake"}):
                with patch("adguard_api.AdGuardAPI",API):
                    with self.assertRaisesRegex(ValueError,"contaminates"):
                        runner.benchmark_due_with_config(self.config(),{},scan,100,"config.json",
                          lambda *a,**k:self.fail("no benchmark should run"))
    def test_config_rejects_unsafe_auto_defaults(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/"config.json"
            config.write_text(json.dumps({"auto_benchmark":True,"trusted_baselines":{}}))
            with self.assertRaises(ValueError):Settings.load(config)
if __name__=="__main__":unittest.main()
