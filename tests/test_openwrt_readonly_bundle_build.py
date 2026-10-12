"""Build a temporary deploy artifact, inspect its actual files/imports and reject tampering."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build,verify,DENIED,imports
class BundleTests(unittest.TestCase):
 def test_minimal_artifact_manifest_and_imports(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(__file__).resolve().parents[1]/"openwrt"
   destination=Path(d)/"readonly"
   result=build(source,destination)
   self.assertTrue(verify(destination))
   self.assertNotIn("rewrite_tx.py",result["files"])
   self.assertNotIn("adguard_api.py",result["files"])
   for name in result["files"]:
    self.assertFalse(imports((destination/name).read_text())&DENIED)
   self.assertEqual(set(x.name for x in destination.iterdir()),set(result["files"])|{"manifest.json"})
 def test_artifact_mutation_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/"readonly";build(Path(__file__).resolve().parents[1]/"openwrt",dest)
   (dest/"runner.py").write_text((dest/"runner.py").read_text()+"\n# tampered\n")
   with self.assertRaisesRegex(ValueError,"modified"):
    verify(dest)
 def test_extra_write_module_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(__file__).resolve().parents[1]/"openwrt";dest=Path(d)/"readonly"
   build(source,dest)
   (dest/"rewrite_tx.py").write_text("print('not executed')\n")
   with self.assertRaisesRegex(ValueError,"unexpected packaged"):
    verify(dest)
if __name__=="__main__":unittest.main()
