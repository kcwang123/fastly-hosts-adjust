import importlib.util,pathlib,sys,unittest
from unittest.mock import Mock
p=pathlib.Path(__file__).resolve().parents[1]/"openwrt"
spec=importlib.util.spec_from_file_location("egress_reflector",p/"egress_reflector.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class ReflectorTests(unittest.TestCase):
 def test_allowlist(self):
  for x in ("http://api.ipify.org/ip","https://example.org/ip","https://user:pass@api.ipify.org/ip","https://api.ipify.org:8443/ip"):
   with self.assertRaises(ValueError):m.inspect_reflector(x)
 def test_bounded_read_only(self):
  response=Mock(status=200);response.getheader.return_value="7";response.read.return_value=b"8.8.8.8"
  client=Mock();client.getresponse.return_value=response
  data=m.probe("https://api.ipify.org/ip",connector=lambda *a,**kw:client)
  self.assertFalse(data["target_path_verified"])
  self.assertFalse(data["safe_to_apply"])
  response.read.assert_called_with(65)
 def test_redirect_and_large_rejected(self):
  response=Mock(status=302);client=Mock();client.getresponse.return_value=response
  with self.assertRaises(ValueError):m.probe("https://api.ipify.org/ip",connector=lambda *a,**kw:client)
  response.status=200;response.getheader.return_value="100"
  with self.assertRaises(ValueError):m.probe("https://api.ipify.org/ip",connector=lambda *a,**kw:client)
if __name__=="__main__":unittest.main()
