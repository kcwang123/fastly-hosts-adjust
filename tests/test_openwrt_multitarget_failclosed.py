"""Multi-target fail-closed runner: no success marker on degraded evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings
T1={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
T2={"domain":"static-cdn.jtvnw.net","baseline_ip":"151.101.2.214","candidate_ip":"151.101.1.214"}

def document(target,fast):
 return {"schema_version":2,"safe_to_apply":False,"bytes_downloaded":600,
         "measurements":[{"domain":target["domain"],"ip":target["candidate_ip"],
             "sni_domain":target["domain"],"tls_verified":True,"http_status":206,
             "baseline_mbps":[10,10,10],"candidate_mbps":[fast]*3}]}

class MultiTargetTests(unittest.TestCase):
 def test_regression_does_not_claim_safe_to_apply(self):
  with tempfile.TemporaryDirectory() as d:
   scan=Path(d)/"scan.json";state=Path(d)/"state.json"
   cfg=Settings(benchmark_targets=(T1,T2),max_benchmark_bytes=1200,
                benchmark_sample_bytes=100,benchmark_rounds=3)
   count=[0]
   def exec(cmd,**kw):
    i=count[0];count[0]+=1
    Path(cmd[cmd.index("--output")+1]).write_text(json.dumps(document((T1,T2)[i],5 if i else 20)))
    return Mock(returncode=0)
   result=runner.run_once(cfg,state,scan,10000,executor=exec,config_path="config.json")
   self.assertEqual(result["status"],"ok")
   self.assertFalse(result["safe_to_apply"])
   self.assertEqual(count[0],2)
 def test_second_target_timeout_never_updates_state(self):
  with tempfile.TemporaryDirectory() as d:
   scan=Path(d)/"scan.json";state=Path(d)/"state.json"
   cfg=Settings(benchmark_targets=(T1,T2),max_benchmark_bytes=1200,benchmark_sample_bytes=100)
   count=[0]
   def exec(cmd,**kw):
    i=count[0];count[0]+=1
    if i: raise TimeoutError("second target timed out")
    Path(cmd[cmd.index("--output")+1]).write_text(json.dumps(document(T1,20)))
    return Mock(returncode=0)
   outcome=runner.run_once(cfg,state,scan,10000,executor=exec,config_path="config.json")
   self.assertEqual(outcome["status"],"error")
   self.assertFalse(state.exists())
 def test_multi_target_aggregate_budget_rejects_before_network(self):
  cfg=Settings(benchmark_targets=(T1,T2),max_benchmark_bytes=1199,
               benchmark_sample_bytes=100)
  with self.assertRaisesRegex(ValueError,"budget"):
   runner.benchmark_due_with_config(cfg,{},Path("/tmp/unread.json"),10,"test.json",
     lambda *a,**k:self.fail("should not spawn"))
if __name__=="__main__":unittest.main()
