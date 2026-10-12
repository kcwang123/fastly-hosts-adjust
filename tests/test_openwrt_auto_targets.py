import importlib.util
from pathlib import Path
import sys
import unittest
r=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(r))
spec=importlib.util.spec_from_file_location("auto_targets",r/"auto_targets.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
SCAN={"schema_version":1,"evidence":"latency_only","safe_to_apply":False,
      "candidates":[{"service":"github","ip":"151.101.1.133","latency_ms":10}]}
PIN={"raw.githubusercontent.com":"151.101.2.133"}
class AutoTargetsTests(unittest.TestCase):
    def test_pinned_baseline(self):
        self.assertEqual(m.select(SCAN,PIN,[])[0]["candidate_ip"],"151.101.1.133")
    def test_dns_rewrite_blocks_even_if_identical(self):
        with self.assertRaisesRegex(ValueError,"contaminates"):
            m.select(SCAN,PIN,[{"domain":"raw.githubusercontent.com","answer":"151.101.2.133"}])
    def test_no_system_resolver_fallback(self):
        with self.assertRaises(ValueError):m.select(SCAN,{},[])
    def test_invalid_evidence(self):
        with self.assertRaises(ValueError):m.select({**SCAN,"safe_to_apply":True},PIN,[])
if __name__=="__main__":unittest.main()
