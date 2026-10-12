"""Cross-target replay and tampering must not update either scheduler timestamp."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings
from benchmark_v3 import verify
from speed_contract import check_evidence
T1={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
T2={"domain":"static-cdn.jtvnw.net","baseline_ip":"151.101.2.214","candidate_ip":"151.101.1.214"}
def evidence(t):
 rows=[]
 for n in range(3):
  for label in ("baseline","candidate"):
   speed=10 if label=="baseline" else 20
   rows.append({"round":n,"label":label,"domain":t["domain"],
    "ip":t[label+"_ip"],"sni_domain":t["domain"],"tls_verified":True,
    "status":206,"etag":'"v1"',"cache_state":"HIT",
    "content_range":"bytes 0-99/200","content_length":100,
    "bytes":100,"duration_seconds":0.0008/speed,"mbps":speed})
 raw={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":600,
      "measurements":[{"domain":t["domain"],"ip":t["candidate_ip"],
      "sni_domain":t["domain"],"tls_verified":True,"http_status":206,
      "baseline_mbps":[10]*3,"candidate_mbps":[20]*3}]}
 return {"schema_version":3,"samples":rows,"evidence":raw,
 "evaluation":check_evidence(raw,max_bytes=1200,min_improvement_percent=15,minimum_rounds=3),
 "diagnostics":{"cv_percent":{"baseline_mbps":0.0,"candidate_mbps":0.0},
 "cache_state":"HIT","etag":'"v1"'},"dry_run":True}
class AttackMatrix(unittest.TestCase):
 def test_tampering_never_advances_state(self):
  cfg=Settings(benchmark_targets=(T1,T2),benchmark_sample_bytes=100,max_benchmark_bytes=1200)
  base=evidence(T2)
  for name,mutate in (
   ("etag",lambda x:x["samples"][0].update(etag='"evil"')),
   ("cache",lambda x:x["samples"][0].update(cache_state="MISS")),
   ("range",lambda x:x["samples"][0].update(content_range="bytes 1-100/200")),
   ("duration",lambda x:x["samples"][0].update(duration_seconds=999)),
   ("cv",lambda x:x["diagnostics"]["cv_percent"].update(candidate_mbps=99)),
   ("bytes",lambda x:x["samples"][0].update(bytes=101)),
   ("missing",lambda x:x["samples"].pop()),
   ("replay",lambda x:x["samples"][0].update(domain=T1["domain"]))):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    p=Path(d);state=p/"state";scan=p/"scan"
    runner.atomic_json(state,{"last_health_epoch":88,"last_benchmark_epoch":77})
    doc=copy.deepcopy(base);mutate(doc);count=[0]
    def execute(cmd,**kwargs):
     i=count[0];count[0]+=1
     Path(cmd[cmd.index("--output")+1]).write_text(json.dumps(evidence(T1) if i==0 else doc))
     return Mock(returncode=0)
    out=runner.run_once(cfg,state,scan,100000,executor=execute,config_path="config.json")
    self.assertEqual(out["status"],"error")
    self.assertEqual(runner.read_state(state),{"last_health_epoch":88,"last_benchmark_epoch":77})
    self.assertEqual(count[0],2)
if __name__=="__main__":unittest.main()
