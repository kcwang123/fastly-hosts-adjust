import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("transaction_cli",root/"transaction_cli.py")
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
from settings import Settings
D="raw.githubusercontent.com"; A="151.101.1.133"; B="151.101.2.133"
class FakeAPI:
    def __init__(self):self.data={}
    def list(self):return [{"domain":k,"answer":v} for k,v in self.data.items()]
    def add(self,d,v):self.data[d]=v
    def delete(self,d,v):
        if self.data.get(d)!=v:raise ValueError("drift")
        del self.data[d]

class EntryTests(unittest.TestCase):
    def env(self,path,write=False):
        p=Path(path); d=p/"state";d.mkdir(mode=0o700)
        return Settings(ownership_registry_path=str(d/"owned.json"),
                        transaction_snapshot_path=str(d/"journal.json"),
                        dry_run=not write)
    def test_preview_no_change(self):
        with tempfile.TemporaryDirectory() as p:
            cfg=self.env(p);api=FakeAPI()
            output=mod.execute(cfg,api,desired={D:A})
            self.assertTrue(output["dry_run"]);self.assertFalse(api.data)
    def test_explicit_apply_requires_disable_dryrun(self):
        with tempfile.TemporaryDirectory() as p:
            cfg=self.env(p);api=FakeAPI()
            with self.assertRaisesRegex(ValueError,"lacks atomic CAS"):
                mod.execute(cfg,api,desired={D:A},mode="apply")
    def test_write_paths_permanently_blocked(self):
        with tempfile.TemporaryDirectory() as p:
            cfg=self.env(p,write=True);api=FakeAPI()
            with self.assertRaisesRegex(ValueError,"lacks atomic CAS"):
                mod.execute(cfg,api,desired={D:A},mode="apply")
            with self.assertRaisesRegex(ValueError,"lacks atomic CAS"):
                mod.execute(cfg,api,mode="recover")
            self.assertFalse(api.data)

    def test_pending_journal_blocks_apply(self):
        with tempfile.TemporaryDirectory() as p:
            cfg=self.env(p,write=True);api=FakeAPI()
            snap=Path(cfg.transaction_snapshot_path);snap.write_text("{}");snap.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"lacks atomic CAS"):
                mod.execute(cfg,api,desired={D:A},mode="apply")
if __name__=="__main__":unittest.main()
