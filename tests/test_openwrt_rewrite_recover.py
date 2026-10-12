import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("rewrite_recover",root/"rewrite_recover.py")
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

D="raw.githubusercontent.com";A="151.101.1.133";B="151.101.2.133"
class API:
    def __init__(self,data):self.data=dict(data)
    def list(self):return [{"domain":k,"answer":v} for k,v in self.data.items()]
    def add(self,d,v):self.data[d]=v
    def delete(self,d,v):
        if self.data.get(d)!=v:raise ValueError("drift")
        del self.data[d]

class RecoveryTests(unittest.TestCase):
    def fixture(self,path,before,owned,desired):
        registry=Path(path)/"ownership.json"; snapshot=Path(path)/"snapshot.json"
        snapshot.write_text(json.dumps({"version":1,"before":before,"ownership_before":owned,"desired":desired}))
        snapshot.chmod(0o600)
        if owned:
            registry.write_text(json.dumps(owned)); registry.chmod(0o600)
        return registry,snapshot
    def test_rollback_update_after_interruption(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({D:B,"unrelated.example":"8.8.8.8"})
            reg,snap=self.fixture(d,{D:A,"unrelated.example":"8.8.8.8"},{D:A},{D:B})
            self.assertEqual(mod.recover(api,reg,snap)["actions"][0]["restore"],A)
            self.assertEqual(api.data[D],B)
            self.assertEqual(mod.recover(api,reg,snap,dry_run=False)["restored"],1)
            self.assertEqual(api.data[D],A)
            self.assertEqual(api.data["unrelated.example"],"8.8.8.8")
            self.assertEqual(json.loads(reg.read_text()),{D:A})
            self.assertFalse(snap.exists())
    def test_interrupted_delete_before_add(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({});reg,snap=self.fixture(d,{D:A},{D:A},{D:B})
            mod.recover(api,reg,snap,dry_run=False)
            self.assertEqual(api.data[D],A)
    def test_no_unowned_takeover(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({D:"151.101.3.133"});reg,snap=self.fixture(d,{}, {}, {D:B})
            with self.assertRaisesRegex(ValueError,"concurrent"):
                mod.recover(api,reg,snap,dry_run=False)
            self.assertTrue(snap.exists())
    def test_new_entry_removed(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({D:B});reg,snap=self.fixture(d,{}, {}, {D:B})
            mod.recover(api,reg,snap,dry_run=False)
            self.assertNotIn(D,api.data)
if __name__=="__main__":unittest.main()
