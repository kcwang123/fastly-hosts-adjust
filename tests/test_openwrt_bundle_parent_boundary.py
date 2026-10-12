"""Fail closed when a replaceable parent can swap the entire bundle."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build,verify
class ParentBoundary(unittest.TestCase):
 def test_writable_immediate_parent_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   parent=Path(d)/"parent";parent.mkdir(mode=0o700)
   artifact=parent/"bundle";build(Path(__file__).resolve().parents[1]/"openwrt",artifact)
   parent.chmod(0o770)
   try:
    with self.assertRaisesRegex(ValueError,"writable bundle parent"):verify(artifact)
   finally:parent.chmod(0o700)
 def test_symlinked_parent_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   parent=Path(d)/"owned";parent.mkdir(mode=0o700)
   artifact=parent/"bundle";build(Path(__file__).resolve().parents[1]/"openwrt",artifact)
   alias=Path(d)/"alias";alias.symlink_to(parent,target_is_directory=True)
   with self.assertRaisesRegex(ValueError,"unsafe bundle parent"):
    verify(alias/"bundle")
if __name__=="__main__":unittest.main()
