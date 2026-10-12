import importlib.util,json,pathlib,sys,unittest
from unittest.mock import Mock
p=pathlib.Path(__file__).resolve().parents[1]/"openwrt"
spec=importlib.util.spec_from_file_location("route_observer",p/"route_observer.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
T={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
class ObserverTests(unittest.TestCase):
 def test_read_only_and_no_egress_attestation(self):
  cmds=[]
  def runner(argv,**kwargs):
   cmds.append(argv);return Mock(returncode=0,stdout=argv[-1]+" via 192.0.2.1 dev eth1 src 192.168.1.240")
  x=m.observe([T],runner=runner,now=100)
  self.assertFalse(x["public_egress_verified"])
  self.assertEqual(x["method"],"local-ip-route-get")
  self.assertEqual(cmds,[["ip","-4","route","get",T["baseline_ip"]],["ip","-4","route","get",T["candidate_ip"]]])
 def test_route_failure_is_fail_closed(self):
  with self.assertRaises(ValueError):m.observe([T],runner=lambda *a,**kw:Mock(returncode=1,stdout=""))
 def test_integrity_rejects_tamper(self):
  s=m.seal({"a":1},b"x"*32)
  self.assertEqual(m.verify_seal(s,b"x"*32),{"a":1})
  s["payload"]["a"]=2
  with self.assertRaises(ValueError):m.verify_seal(s,b"x"*32)
 def test_no_fake_egress_contract(self):
  sys.path.insert(0,str(p))
  from egress_contract import validate_evidence
  doc=m.observe([T],runner=lambda *a,**kw:Mock(returncode=0,stdout="151.101.2.133 dev eth1"),now=100)
  with self.assertRaises(ValueError):validate_evidence(doc,targets=[T],max_age_seconds=300,now=200)
if __name__=="__main__":unittest.main()
