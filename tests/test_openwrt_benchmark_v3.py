import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import benchmark_v3
from settings import Settings
from speed_contract import check_evidence
TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
CFG=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,max_benchmark_bytes=600)
def fixture():
 rows=[]
 for n in range(3):
  for label in ("baseline","candidate"):
   speed=10.0 if label=="baseline" else 20.0
   rows.append({"round":n,"label":label,"domain":TARGET["domain"],
    "ip":TARGET[label+"_ip"],"sni_domain":TARGET["domain"],"tls_verified":True,
    "status":206,"etag":'"v1"',"cache_state":"HIT","content_range":"bytes 0-99/200",
    "content_length":100,"bytes":100,"duration_seconds":800/1000000/speed,"mbps":speed})
 evidence={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":600,
  "measurements":[{"domain":TARGET["domain"],"ip":TARGET["candidate_ip"],
  "sni_domain":TARGET["domain"],"tls_verified":True,"http_status":206,
  "baseline_mbps":[10.0]*3,"candidate_mbps":[20.0]*3}]}
 return {"schema_version":3,"samples":rows,"evidence":evidence,
  "evaluation":check_evidence(evidence,max_bytes=600,min_improvement_percent=15,
  minimum_rounds=3),"diagnostics":{"cv_percent":{"baseline_mbps":0.0,"candidate_mbps":0.0},
  "etag":'"v1"',"cache_state":"HIT"},"dry_run":True}
class V3Tests(unittest.TestCase):
 def verify(self,value):return benchmark_v3.verify(value,CFG,expected_target=TARGET)
 def test_valid_v3(self):self.assertFalse(self.verify(fixture())["safe_to_apply"])
 def test_v2_rejected(self):
  v=fixture();v.pop("samples");v.pop("schema_version")
  with self.assertRaises(ValueError):self.verify(v)
 def test_tampered_target_rejected(self):
  v=fixture();v["samples"][1]["ip"]="151.101.3.133"
  with self.assertRaises(ValueError):self.verify(v)
 def test_tampered_cv_rejected(self):
  v=fixture();v["diagnostics"]["cv_percent"]["candidate_mbps"]=31.0
  with self.assertRaises(ValueError):self.verify(v)
 def test_etag_mismatch_rejected(self):
  v=fixture();v["samples"][1]["etag"]='"v2"'
  with self.assertRaises(ValueError):self.verify(v)
 def test_wrong_duration_rejected(self):
  v=fixture();v["samples"][1]["duration_seconds"]*=2
  with self.assertRaises(ValueError):self.verify(v)
 def test_missing_round_rejected(self):
  v=fixture();v["samples"].pop()
  with self.assertRaises(ValueError):self.verify(v)
 def test_duplicate_round_rejected(self):
  v=fixture();v["samples"][1]["round"]=0;v["samples"][1]["label"]="baseline"
  with self.assertRaises(ValueError):self.verify(v)
 def test_cache_mismatch_rejected(self):
  v=fixture();v["samples"][1]["cache_state"]="MISS"
  with self.assertRaises(ValueError):self.verify(v)
if __name__=="__main__":unittest.main()
