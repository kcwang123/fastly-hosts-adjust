import importlib.util
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("route_proposal",root/"route_proposal.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
SCAN={"schema_version":1,"evidence":"latency_only","safe_to_apply":False,
      "candidates":[{"service":"github","ip":"151.101.1.133","latency_ms":9},
                    {"service":"github","ip":"151.101.2.133","latency_ms":20}]}
class ProposalTests(unittest.TestCase):
    def test_selects_distinct_and_fastest(self):
        p=m.propose(SCAN,lambda domain:"151.101.2.133")
        self.assertEqual(p["targets"][0]["candidate_ip"],"151.101.1.133")
        self.assertFalse(p["safe_to_apply"])
    def test_rejects_invalid_baseline(self):
        with self.assertRaises(ValueError):m.propose(SCAN,lambda _: "127.0.0.1")
    def test_contract_fail_closed(self):
        with self.assertRaises(ValueError):m.propose({**SCAN,"safe_to_apply":True},lambda _:"151.101.2.133")
    def test_no_same_ip(self):
        data={**SCAN,"candidates":[SCAN["candidates"][0]]}
        with self.assertRaises(ValueError):m.propose(data,lambda _:"151.101.1.133")
if __name__=="__main__":unittest.main()
