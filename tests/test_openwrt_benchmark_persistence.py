"""Ensure corrupt persisted diagnostics never advance the Runner state."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from speed_contract import check_evidence
from settings import Settings
TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
RAW={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":600,
     "measurements":[{"domain":"raw.githubusercontent.com","ip":"151.101.1.133",
        "sni_domain":"raw.githubusercontent.com","tls_verified":True,"http_status":206,
        "baseline_mbps":[10,10,10],"candidate_mbps":[20,20,20]}]}
class PersistedEnvelope(unittest.TestCase):
 def test_invalid_cv_diagnostics_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   cfg=Settings(benchmark_targets=(TARGET,),benchmark_sample_bytes=100,max_benchmark_bytes=600)
   state=Path(d)/"state";scan=Path(d)/"scan"
   def execute(cmd,**kw):
    data={"evidence":RAW,"evaluation":check_evidence(RAW,max_bytes=600,
           min_improvement_percent=15,minimum_rounds=3),"dry_run":True,
          "diagnostics":{"cv_percent":{"baseline_mbps":99.0,"candidate_mbps":0.0},
                         "cache_state":"HIT","etag":'"one"'}}
    Path(cmd[cmd.index("--output")+1]).write_text(json.dumps(data))
    return Mock(returncode=0)
   out=runner.run_once(cfg,state,scan,123456,executor=execute,config_path="config.json")
   self.assertEqual(out["status"],"error")
   self.assertFalse(state.exists())
if __name__=="__main__":unittest.main()
