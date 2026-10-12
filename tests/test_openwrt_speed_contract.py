import importlib.util
from pathlib import Path
import sys
import unittest
r=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(r))
spec=importlib.util.spec_from_file_location("speed_contract",r/"speed_contract.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
GOOD={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":1000,
      "measurements":[{"domain":"raw.githubusercontent.com","ip":"151.101.1.133",
      "tls_verified":True,"sni_domain":"raw.githubusercontent.com","http_status":200,
      "baseline_mbps":[10,11,12],"candidate_mbps":[15,18,19]}]}
class ContractTests(unittest.TestCase):
    def test_speed_median_and_threshold(self):
        x=m.check_evidence(GOOD,max_bytes=2000,min_improvement_percent=15)
        self.assertTrue(x["results"][0]["passes_threshold"])
        self.assertFalse(x["safe_to_apply"])
    def test_reject_budget_tls_sni_and_fake_success(self):
        import copy
        for update in ({"bytes_downloaded":2001},{"safe_to_apply":True}):
            item=copy.deepcopy(GOOD);item.update(update)
            with self.assertRaises(ValueError):m.check_evidence(item,max_bytes=2000,min_improvement_percent=15)
        for key,val in (("tls_verified",False),("sni_domain","example.com"),
                        ("candidate_mbps",[1]),("http_status",500)):
            item=copy.deepcopy(GOOD);item["measurements"][0][key]=val
            with self.assertRaises(ValueError):m.check_evidence(item,max_bytes=2000,min_improvement_percent=15)
if __name__=="__main__":unittest.main()
