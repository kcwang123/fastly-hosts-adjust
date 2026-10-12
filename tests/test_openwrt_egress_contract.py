import importlib.util, pathlib, sys, unittest
p=pathlib.Path(__file__).resolve().parents[1]/"openwrt";sys.path.insert(0,str(p))
spec=importlib.util.spec_from_file_location("egress_contract",p/"egress_contract.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
T={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
O={**T,"baseline_egress_ip":"1.1.1.1","candidate_egress_ip":"1.1.1.1",
   "baseline_interface":"eth1","candidate_interface":"eth1","baseline_route":"via 192.0.2.1",
   "candidate_route":"via 192.0.2.1","method":"independent-https-probe-per-route"}
D={"version":1,"observed_epoch":100,"observations":[O],"read_only":True}
class EgressTests(unittest.TestCase):
 def check(self,v):return m.validate_evidence(v,targets=[T],max_age_seconds=300,now=200)
 def test_valid(self):self.assertTrue(self.check(D)["egress_consistent"])
 def test_differing_exit_fails(self):
  with self.assertRaisesRegex(ValueError,"different public"):self.check({**D,"observations":[{**O,"candidate_egress_ip":"8.8.8.8"}]})
 def test_stale_fails(self):
  with self.assertRaisesRegex(ValueError,"stale"):self.check({**D,"observed_epoch":-400})
 def test_route_only_fails(self):
  with self.assertRaisesRegex(ValueError,"route dump"):self.check({**D,"observations":[{**O,"method":"ip-route-get"}]})
 def test_interface_mismatch(self):
  with self.assertRaisesRegex(ValueError,"interface"):self.check({**D,"observations":[{**O,"candidate_interface":"wg0"}]})
if __name__=="__main__":unittest.main()
