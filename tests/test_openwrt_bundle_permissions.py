"""Package permissions are a real local trust boundary, not an OS sandbox."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build,verify
class Permissions(unittest.TestCase):
 def test_untrusted_writable_modes_rejected(self):
  source=Path(__file__).resolve().parents[1]/"openwrt"
  for name in ("bundle","manifest.json","runner.py"):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    dest=Path(d)/"bundle";build(source,dest)
    target=dest if name=="bundle" else dest/name
    target.chmod(target.stat().st_mode | 0o020)
    with self.assertRaisesRegex(ValueError,"writable"):
     verify(dest)
 def test_owner_writability_does_not_establish_independent_trust(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/"bundle";build(Path(__file__).resolve().parents[1]/"openwrt",dest)
   self.assertTrue(verify(dest))
   # The builder and runtime share this UID in CI. No independent trust root.
   self.assertTrue(bool(dest.stat().st_mode & 0o200))
if __name__=="__main__":unittest.main()
