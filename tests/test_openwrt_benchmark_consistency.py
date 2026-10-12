import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import https_benchmark as bench
from settings import Settings
BASE="151.101.2.133"
CAND="151.101.1.133"
class ConsistencyTests(unittest.TestCase):
 def run_benchmark(self, behavior):
  calls=[0]
  def sample(domain,ip,limit,*timeouts):
   index=calls[0];calls[0]+=1
   meta=behavior(index,ip)
   return {"bytes":limit,"status":206,"tls_verified":True,
           "mbps":meta.get("mbps",10),"etag":meta.get("etag"),
           "cache_state":meta.get("cache_state","UNKNOWN")}
  cfg=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,
               max_benchmark_bytes=600,max_sample_cv_percent=35.0)
  return bench.benchmark("raw.githubusercontent.com",BASE,CAND,cfg,sampler=sample)
 def test_same_etag_and_cache(self):
  data=self.run_benchmark(lambda i,ip:{"etag":'"v1"',"cache_state":"HIT"})
  self.assertEqual(data["diagnostics"]["etag"],'"v1"')
  self.assertEqual(data["diagnostics"]["cv_percent"]["baseline_mbps"],0)
 def test_mixed_etags_rejected(self):
  with self.assertRaisesRegex(ValueError,"ETag"):
   self.run_benchmark(lambda i,ip:{"etag":'"v1"' if ip==BASE else '"v2"'})
 def test_missing_etag_with_present_etag_rejected(self):
  with self.assertRaisesRegex(ValueError,"ETag"):
   self.run_benchmark(lambda i,ip:{"etag":'"v1"' if ip==BASE else None})
 def test_mixed_cache_rejected(self):
  with self.assertRaisesRegex(ValueError,"cache"):
   self.run_benchmark(lambda i,ip:{"cache_state":"HIT" if ip==BASE else "MISS"})
 def test_jitter_rejected(self):
  with self.assertRaisesRegex(ValueError,"unstable"):
   self.run_benchmark(lambda i,ip:{"mbps":1 if i in (0,1) else 100})
 def test_no_cache_metadata_stays_read_only(self):
  data=self.run_benchmark(lambda i,ip:{})
  self.assertFalse(data["evaluation"]["safe_to_apply"])
if __name__=="__main__":unittest.main()
