"""Fail-closed runner integration when only read-only ip-route observations exist."""
import json, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch, Mock
root=pathlib.Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
import runner
from settings import Settings
SCAN={"schema_version":1,"evidence":"latency_only","safe_to_apply":False,
      "candidates":[{"service":"github","ip":"151.101.1.133","latency_ms":7}]}
BASE="151.101.2.133"
class IntegrationTests(unittest.TestCase):
    def test_route_only_evidence_rejected_before_benchmark(self):
        with tempfile.TemporaryDirectory() as d:
            scan=pathlib.Path(d)/"scan.json";scan.write_text(json.dumps(SCAN))
            evidence=pathlib.Path(d)/"route.json"
            evidence.write_text(json.dumps({"version":1,"observed_epoch":100,
              "method":"local-ip-route-get","read_only":True,
              "public_egress_verified":False,"observations":[]}))
            settings=Settings(auto_benchmark=True,
                trusted_baselines={"raw.githubusercontent.com":BASE},
                egress_evidence_path=str(evidence))
            class AGH:
                def __init__(self,*args): pass
                def list(self): return []
            with patch.dict(os.environ,{"ADGUARD_USER":"test","ADGUARD_PASSWORD":"test"}):
                with patch("adguard_api.AdGuardAPI",AGH):
                    with self.assertRaisesRegex(RuntimeError,"egress unavailable"):
                        runner.benchmark_due_with_config(settings,{},scan,100,"config.json",
                            lambda *args,**kw:self.fail("benchmark must not launch"))
    def test_egress_failure_does_not_advance_state(self):
        with tempfile.TemporaryDirectory() as d:
            state=pathlib.Path(d)/"state.json";scan=pathlib.Path(d)/"scan.json"
            scan.write_text(json.dumps(SCAN))
            settings=Settings(auto_benchmark=True,trusted_baselines={"raw.githubusercontent.com":BASE},
                              egress_evidence_path=str(pathlib.Path(d)/"missing.json"))
            state.write_text(json.dumps({"last_health_epoch":1}))
            class AGH:
                def __init__(self,*args): pass
                def list(self): return []
            with patch.dict(os.environ,{"ADGUARD_USER":"test","ADGUARD_PASSWORD":"test"}):
                with patch("adguard_api.AdGuardAPI",AGH):
                    result=runner.run_once(settings,state,scan,100000,
                        executor=lambda *a,**kw:self.fail("benchmark must not launch"),
                        config_path="config.json")
            self.assertEqual(result["status"],"error")
            self.assertNotIn("last_benchmark_epoch",runner.read_state(state))
if __name__=="__main__":unittest.main()
