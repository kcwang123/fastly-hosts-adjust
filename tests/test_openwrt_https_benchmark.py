import importlib.util
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("https_benchmark",root/"https_benchmark.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
from settings import Settings

class BenchmarkTests(unittest.TestCase):
    def test_budget_reserves_and_refunds(self):
        b=m.Budget(15)
        b.reserve(10);b.finish(10,4)
        self.assertEqual(b.used,4)
        self.assertEqual(b.remaining,11)
        with self.assertRaises(ValueError):b.reserve(12)
    def test_median_and_alternating_rounds(self):
        calls=[]
        def sampler(d,ip,n,*timeouts):
            calls.append(ip)
            return {"bytes":100,"mbps":20 if ip.endswith(".133") else 10,
                    "status":206,"tls_verified":True}
        s=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,max_benchmark_bytes=600)
        x=m.benchmark("raw.githubusercontent.com","151.101.2.133","151.101.1.133",s,sampler=sampler)
        self.assertEqual(x["evidence"]["bytes_downloaded"],600)
        self.assertTrue(x["evaluation"]["results"][0]["passes_threshold"])
        self.assertFalse(x["evaluation"]["safe_to_apply"])
        self.assertEqual(calls[:4],["151.101.2.133","151.101.1.133",
                                    "151.101.1.133","151.101.2.133"])
    def test_hard_budget(self):
        count=[0]
        def sampler(*args):
            count[0]+=1
            return {"bytes":100,"mbps":10,"status":206,"tls_verified":True}
        s=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,max_benchmark_bytes=500)
        with self.assertRaisesRegex(ValueError,"budget"):
            m.benchmark("raw.githubusercontent.com","151.101.2.133","151.101.1.133",s,sampler=sampler)
        self.assertEqual(count[0],5)
    def test_tls_failure_and_timeout(self):
        s=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,max_benchmark_bytes=600)
        def fail(*args):raise TimeoutError()
        with self.assertRaises(TimeoutError):
            m.benchmark("raw.githubusercontent.com","151.101.2.133","151.101.1.133",s,sampler=fail)
        def bad(*args):return {"bytes":100,"mbps":10,"status":206,"tls_verified":False}
        with self.assertRaisesRegex(ValueError,"verification"):
            m.benchmark("raw.githubusercontent.com","151.101.2.133","151.101.1.133",s,sampler=bad)
    def test_performance_regression_not_approved(self):
        s=Settings(benchmark_rounds=3,benchmark_sample_bytes=100,max_benchmark_bytes=600)
        def slow(d,ip,n,*args):
            return {"bytes":100,"mbps":5 if ip.endswith(".1.133") else 20,
                    "status":206,"tls_verified":True}
        x=m.benchmark("raw.githubusercontent.com","151.101.2.133","151.101.1.133",s,sampler=slow)
        self.assertFalse(x["evaluation"]["results"][0]["passes_threshold"])
if __name__=="__main__":unittest.main()
