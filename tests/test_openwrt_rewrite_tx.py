import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock

root=pathlib.Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("rewrite_tx",root/"rewrite_tx.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
D="raw.githubusercontent.com"
A="151.101.1.133"
B="151.101.2.133"

class API:
    def __init__(self,rows=None,fail_add=False):
        self.rows=dict(rows or {})
        self.fail_add=fail_add
    def list(self):
        return [{"domain":k,"answer":v} for k,v in self.rows.items()]
    def add(self,d,a):
        if self.fail_add:
            self.fail_add=False
            raise OSError("simulated API error")
        if d in self.rows: raise ValueError("duplicate")
        self.rows[d]=a
    def delete(self,d,a):
        if self.rows.get(d)!=a: raise ValueError("mismatch")
        del self.rows[d]

class TxTests(unittest.TestCase):
    def paths(self,base):
        return pathlib.Path(base)/"ownership.json",pathlib.Path(base)/"snapshot.json"
    def test_dry_run_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            api=API();reg,snap=self.paths(d)
            self.assertTrue(m.reconcile(api,{D:A},reg,snap)["dry_run"])
            self.assertEqual(api.rows,{})
            self.assertFalse(snap.exists())
    def test_create_and_update_owned(self):
        with tempfile.TemporaryDirectory() as d:
            api=API();reg,snap=self.paths(d)
            m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertEqual(api.rows[D],A)
            self.assertFalse(snap.exists())
            m.reconcile(api,{D:B},reg,snap,dry_run=False)
            self.assertEqual(api.rows[D],B)
    def test_existing_unowned_even_identical_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({D:A});reg,snap=self.paths(d)
            with self.assertRaisesRegex(ValueError,"unowned"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertFalse(reg.exists())
    def test_failure_rolls_back_and_does_not_claim_ownership(self):
        with tempfile.TemporaryDirectory() as d:
            api=API(fail_add=True);reg,snap=self.paths(d)
            with self.assertRaisesRegex(RuntimeError,"rollback completed"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertEqual(api.rows,{})
            self.assertFalse(reg.exists())
            self.assertFalse(snap.exists())
    def test_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            api=API({D:B});reg,snap=self.paths(d)
            m.atomic_save(reg,{D:A})
            with self.assertRaisesRegex(ValueError,"drift"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertEqual(api.rows[D],B)
    def test_write_intent_is_durable_before_api_change(self):
        with tempfile.TemporaryDirectory() as d:
            reg,snap=self.paths(d)
            class InspectAPI(API):
                def add(self, domain, value):
                    import json
                    journal=json.loads(snap.read_text())
                    self.assert_journal(journal,domain,value)
                    super().add(domain,value)
                def assert_journal(self, journal, domain, value):
                    assert journal["phase"] == "applying"
                    assert journal["last_intent"]["domain"] == domain
                    assert journal["last_intent"]["target"] == value
            api=InspectAPI()
            m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertFalse(snap.exists())
    def test_api_commits_then_loses_response_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            reg,snap=self.paths(d)
            class LostReplyAPI(API):
                def add(self,domain,value):
                    super().add(domain,value)
                    if not getattr(self,"lost",False):
                        self.lost=True
                        raise TimeoutError("response lost after write")
            api=LostReplyAPI()
            with self.assertRaisesRegex(RuntimeError,"rollback completed"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertNotIn(D,api.rows)
            self.assertFalse(reg.exists())
    def test_rollback_failure_keeps_journal(self):
        with tempfile.TemporaryDirectory() as d:
            reg,snap=self.paths(d)
            class FailRollbackAPI(API):
                def add(self,domain,value):
                    super().add(domain,value)
                    raise OSError("lost response")
                def delete(self,domain,value):
                    raise OSError("rollback blocked")
            api=FailRollbackAPI()
            with self.assertRaisesRegex(RuntimeError,"rollback incomplete"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
            self.assertTrue(snap.exists())
            self.assertEqual(api.rows[D],A)
    def test_existing_snapshot_blocks_reentry(self):
        with tempfile.TemporaryDirectory() as d:
            api=API();reg,snap=self.paths(d);snap.write_text("{}");snap.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"snapshot already exists"):
                m.reconcile(api,{D:A},reg,snap,dry_run=False)
if __name__=="__main__":unittest.main()
