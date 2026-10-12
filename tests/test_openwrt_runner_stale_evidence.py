"""Runner must never accept stale or malformed subprocess output."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings
TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
class FailClosedEvidence(unittest.TestCase):
 def test_stale_artifact_cannot_advance_success_state(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);scan=p/"scan.json";state=p/"state.json"
   stale=Path(str(scan)+".benchmark.0.json")
   stale.write_text(json.dumps({"schema_version":3,"dry_run":True,"unverified":"leftover"}))
   cfg=Settings(benchmark_targets=(TARGET,),benchmark_sample_bytes=100,max_benchmark_bytes=600)
   result=runner.run_once(cfg,state,scan,12345,config_path="config.json",
     executor=lambda *args,**kwargs: Mock(returncode=0))
   self.assertEqual(result["status"],"error")
   self.assertFalse(stale.exists())
   self.assertFalse(state.exists())
 def test_subprocess_timeout_cannot_use_previous_success(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);scan=p/"scan.json";state=p/"state.json"
   runner.atomic_json(state,{"last_health_epoch":1})
   cfg=Settings(benchmark_targets=(TARGET,),benchmark_sample_bytes=100,max_benchmark_bytes=600)
   def timeout(*args,**kw):raise TimeoutError("child timed out")
   result=runner.run_once(cfg,state,scan,12345,config_path="config.json",executor=timeout)
   self.assertEqual(result["status"],"error")
   self.assertEqual(runner.read_state(state),{"last_health_epoch":1})
if __name__=="__main__":unittest.main()
