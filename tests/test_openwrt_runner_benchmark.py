import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("runner_ext",root/"runner.py")
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m;spec.loader.exec_module(m)
from settings import Settings
TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133",
        "candidate_ip":"151.101.1.133"}
GOOD={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":600,
      "measurements":[{"domain":"raw.githubusercontent.com","ip":"151.101.1.133",
      "tls_verified":True,"sni_domain":"raw.githubusercontent.com","http_status":206,
      "baseline_mbps":[10,10,10],"candidate_mbps":[16,16,16]}]}

class RunnerBenchmarkTests(unittest.TestCase):
    def test_due_benchmark_updates_both_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json"; scan=Path(d)/"scan.json"
            cfg=Settings(benchmark_targets=(TARGET,),benchmark_rounds=3,
                         benchmark_sample_bytes=100,max_benchmark_bytes=600)
            def execute(cmd, **kwargs):
                Path(cmd[cmd.index("--output")+1]).write_text(json.dumps(GOOD))
                return Mock(returncode=0)
            result=m.run_once(cfg,state,scan,100000,executor=execute,config_path="config.json")
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["mode"],"benchmark")
            self.assertFalse(result["safe_to_apply"])
            self.assertEqual(m.read_state(state)["last_health_epoch"],100000)
            self.assertEqual(m.read_state(state)["last_benchmark_epoch"],100000)
    def test_failed_benchmark_does_not_update_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json";scan=Path(d)/"scan.json"
            cfg=Settings(benchmark_targets=(TARGET,))
            result=m.run_once(cfg,state,scan,100000,
                              executor=lambda *a,**k:Mock(returncode=1),
                              config_path="config.json")
            self.assertEqual(result["status"],"error")
            self.assertFalse(state.exists())
    def test_aggregate_budget_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Settings(benchmark_targets=(TARGET,TARGET),benchmark_rounds=3,
                         benchmark_sample_bytes=100,max_benchmark_bytes=600)
            with self.assertRaisesRegex(ValueError,"global budget"):
                m.benchmark_due_with_config(cfg,{},Path(d)/"scan.json",10000,"config.json",
                    lambda *a,**k:self.fail("must not call network"))
    def test_benchmark_only_after_24h(self):
        cfg=Settings(benchmark_targets=(TARGET,))
        self.assertEqual(m.choose_mode(cfg,{"last_health_epoch":100000,
                          "last_benchmark_epoch":100000},100000+3*3600),"health")
        self.assertEqual(m.choose_mode(cfg,{"last_health_epoch":100000,
                          "last_benchmark_epoch":100000},100000+24*3600),"benchmark")
if __name__=="__main__":unittest.main()
