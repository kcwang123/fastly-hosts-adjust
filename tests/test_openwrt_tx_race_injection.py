"""Isolated failure cases for write barriers: never run against a live router."""
import sys, tempfile, unittest, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import rewrite_tx, rewrite_recover
D="raw.githubusercontent.com"
A="151.101.1.133"; B="151.101.2.133"; C="151.101.3.133"
class Fake:
 def __init__(self): self.data={D:A}; self.calls=0
 def list(self):
  self.calls+=1
  return [{"domain":k,"answer":v} for k,v in self.data.items()]
 def add(self,d,v):
  if d in self.data: raise ValueError("already exists")
  self.data[d]=v
 def delete(self,d,v):
  if self.data.get(d)!=v: raise ValueError("compare failed")
  del self.data[d]
class FailureInjection(unittest.TestCase):
 def test_external_writer_before_mutation_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   reg=Path(d)/"registry.json";snap=Path(d)/"snapshot.json"
   rewrite_tx.atomic_save(reg,{D:A})
   class Race(Fake):
    def list(self):
     x=super().list()
     if self.calls==3:
      self.data[D]=C
      x=[{"domain":D,"answer":C}]
     return x
   api=Race()
   with self.assertRaisesRegex(RuntimeError,"transaction failed"):
    rewrite_tx.reconcile(api,{D:B},reg,snap,dry_run=False)
   self.assertEqual(api.data[D],C)
   self.assertTrue(snap.exists())
 def test_recovery_refuses_unexpected_external_entry(self):
  with tempfile.TemporaryDirectory() as d:
   reg=Path(d)/"registry.json";snap=Path(d)/"snapshot.json"
   rewrite_tx.atomic_save(reg,{D:A})
   rewrite_tx.atomic_save(snap,{"version":1,"before":{D:A},
    "ownership_before":{D:A},"desired":{D:B},"phase":"applying",
    "last_intent":{"domain":D,"old":A,"target":B}})
   api=Fake();api.data[D]=C
   with self.assertRaisesRegex(ValueError,"concurrent"):
    rewrite_recover.recover(api,reg,snap,dry_run=False)
   self.assertEqual(api.data[D],C)
   self.assertTrue(snap.exists())
if __name__=="__main__":unittest.main()
