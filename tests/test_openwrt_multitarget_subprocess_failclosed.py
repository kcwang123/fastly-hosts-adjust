"""Two-target subprocess failure cannot reuse stale evidence or mark benchmark success."""
import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings
T1={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
T2={"domain":"static-cdn.jtvnw.net","baseline_ip":"151.101.2.214","candidate_ip":"151.101.1.214"}
class TwoTarget(unittest.TestCase):
 def test_second_child_failed_after_previous_success_does_not_mark_success(self):
  with tempfile.TemporaryDirectory() as d:
   scan=Path(d)/"scan";state=Path(d)/"state"
   cfg=Settings(benchmark_targets=(T1,T2),benchmark_sample_bytes=100,max_benchmark_bytes=1200)
   for i in range(2):
    Path(str(scan)+".benchmark."+str(i)+".json").write_text('{"schema_version":3,"fake":"stale"}')
   calls=[]
   def child(cmd,**kwargs):
    calls.append(cmd)
    if len(calls)==1:
     out=Path(cmd[cmd.index("--output")+1]);out.write_text('{"schema_version":3,"fake":"unverified"}')
     return Mock(returncode=0)
    return Mock(returncode=1)
   result=runner.run_once(cfg,state,scan,50000,executor=child,config_path="config.json")
   self.assertEqual(result["status"],"error")
   self.assertFalse(state.exists())
   self.assertEqual(len(calls),1)
 def test_second_child_timeout_cannot_advance_state(self):
  with tempfile.TemporaryDirectory() as d:
   scan=Path(d)/"scan";state=Path(d)/"state"
   cfg=Settings(benchmark_targets=(T1,T2),benchmark_sample_bytes=100,max_benchmark_bytes=1200)
   def child(cmd,**kwargs):raise subprocess.TimeoutExpired(cmd,1)
   result=runner.run_once(cfg,state,scan,50000,executor=child,config_path="config.json")
   self.assertEqual(result["status"],"error");self.assertFalse(state.exists())
if __name__=="__main__":unittest.main()
