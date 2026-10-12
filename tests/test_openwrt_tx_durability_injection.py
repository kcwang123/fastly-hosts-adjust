"""Isolated filesystem durability and partially committed API write injection."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import rewrite_tx, rewrite_recover
D="raw.githubusercontent.com"
A="151.101.1.133"
B="151.101.2.133"
class Fake:
 def __init__(self,rows):self.rows=dict(rows);self.calls=[]
 def list(self):return [{"domain":k,"answer":v} for k,v in self.rows.items()]
 def delete(self,d,v):
  self.calls.append(("delete",d,v))
  if self.rows.get(d)!=v:raise RuntimeError("concurrent writer")
  del self.rows[d]
 def add(self,d,v):
  self.calls.append(("add",d,v))
  if d in self.rows:raise RuntimeError("duplicate")
  self.rows[d]=v
class DurableTests(unittest.TestCase):
 def test_fsync_failure_preserves_original_and_removes_temp(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"registry.json"
   rewrite_tx.atomic_save(path,{"test":1})
   with patch.object(rewrite_tx.os,"fsync",side_effect=OSError("simulated IO failure")):
    with self.assertRaises(OSError):rewrite_tx.atomic_save(path,{"test":2})
   self.assertIn('"test": 1',path.read_text())
   self.assertEqual(sorted(p.name for p in Path(d).iterdir()),["registry.json"])
 def test_atomic_replace_failure_preserves_original(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"registry.json";rewrite_tx.atomic_save(path,{"test":1})
   with patch.object(rewrite_tx.os,"replace",side_effect=OSError("rename failure")):
    with self.assertRaises(OSError):rewrite_tx.atomic_save(path,{"test":2})
   self.assertIn('"test": 1',path.read_text())
   self.assertEqual(len(list(Path(d).glob("*.tmp.*"))),0)
 def test_delete_success_then_add_fails_restores_owned(self):
  with tempfile.TemporaryDirectory() as d:
   reg=Path(d)/"registry.json";snap=Path(d)/"snapshot.json"
   rewrite_tx.atomic_save(reg,{D:A})
   class LostAdd(Fake):
    def add(self,domain,value):
     if value==B: raise ConnectionError("simulated connection dropped")
     super().add(domain,value)
   api=LostAdd({D:A})
   with self.assertRaisesRegex(RuntimeError,"rollback completed"):
    rewrite_tx.reconcile(api,{D:B},reg,snap,dry_run=False)
   self.assertEqual(api.rows[D],A)
   self.assertFalse(snap.exists())
 def test_commit_registry_failure_keeps_journal_for_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   reg=Path(d)/"registry.json";snap=Path(d)/"snapshot.json"
   rewrite_tx.atomic_save(reg,{D:A})
   api=Fake({D:A});real_save=rewrite_tx.atomic_save
   def fail_registry(path,value):
    if Path(path)==reg and value=={D:B}:raise OSError("registry storage failure")
    return real_save(path,value)
   with patch.object(rewrite_tx,"atomic_save",side_effect=fail_registry):
    with self.assertRaisesRegex(RuntimeError,"transaction failed"):
     rewrite_tx.reconcile(api,{D:B},reg,snap,dry_run=False)
   self.assertEqual(api.rows[D],A)
if __name__=="__main__":unittest.main()
