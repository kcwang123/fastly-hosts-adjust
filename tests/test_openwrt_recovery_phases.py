"""No real AdGuard calls: verify journal phase crash-window safety."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import rewrite_recover,rewrite_tx
D="raw.githubusercontent.com"; A="151.101.1.133"; B="151.101.2.133"
class Fake:
 def __init__(self,data):self.data=dict(data);self.writes=[]
 def list(self):return [{"domain":k,"answer":v} for k,v in self.data.items()]
 def delete(self,d,v):self.writes.append(("delete",d,v));del self.data[d]
 def add(self,d,v):self.writes.append(("add",d,v));self.data[d]=v
class CrashWindow(unittest.TestCase):
 def setup(self,path,phase):
  reg=Path(path)/"registry.json";snap=Path(path)/"snapshot.json"
  rewrite_tx.atomic_save(reg,{D:A})
  rewrite_tx.atomic_save(snap,{"version":1,"phase":phase,"before":{D:A},
    "ownership_before":{D:A},"desired":{D:B},"last_intent":None})
  return reg,snap
 def test_prepared_journal_external_change_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   reg,snap=self.setup(d,"prepared");api=Fake({D:B})
   with self.assertRaisesRegex(ValueError,"prepared journal"):
    rewrite_recover.recover(api,reg,snap,dry_run=False)
   self.assertEqual(api.writes,[]);self.assertTrue(snap.exists())
 def test_unknown_phase_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   reg,snap=self.setup(d,"mystery");api=Fake({D:B})
   with self.assertRaisesRegex(ValueError,"phase"):
    rewrite_recover.recover(api,reg,snap,dry_run=False)
   self.assertEqual(api.writes,[])
 def test_crash_after_delete_restores_owned_entry(self):
  with tempfile.TemporaryDirectory() as d:
   reg,snap=self.setup(d,"applying");api=Fake({})
   self.assertEqual(rewrite_recover.recover(api,reg,snap,dry_run=False)["restored"],1)
   self.assertEqual(api.data[D],A)
if __name__=="__main__":unittest.main()
