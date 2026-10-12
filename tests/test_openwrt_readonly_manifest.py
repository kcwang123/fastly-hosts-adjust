import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner, readonly_bundle_manifest as manifest
from settings import Settings

class ReadOnlyDeployment(unittest.TestCase):
 def test_runtime_manifest_excludes_writers(self):
  root=Path(__file__).resolve().parents[1]/"openwrt"
  files=set(manifest.validate(root))
  self.assertFalse(files & manifest.FORBIDDEN)
  self.assertNotIn("adguard_api.py",files)
  self.assertIn("runner.py",files)
 def test_auto_benchmark_rejects_before_any_adguard_calls(self):
  config=Settings(auto_benchmark=True)
  with patch.object(runner,"read_state",side_effect=AssertionError("state should not be needed")):
   with self.assertRaisesRegex(RuntimeError,"egress"):
    runner.benchmark_due_with_config(config,{},Path("/nonexistent/scan"),1000,
                                     "config.json",executor=lambda *a,**k:self.fail("no subprocess"))
if __name__=="__main__":unittest.main()
