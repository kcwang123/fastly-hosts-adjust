"""Exercise the exact read-only output directory as an OS subprocess, no network."""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build,verify
class RuntimeSmoke(unittest.TestCase):
 def test_real_bundled_runner_skip_and_isolated_imports(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);dest=root/"bundle";build(Path(__file__).resolve().parents[1]/"openwrt",dest)
   self.assertTrue(verify(dest))
   cfg=root/"config.json";cfg.write_text(json.dumps({"dry_run":True,"auto_benchmark":False}))
   state=root/"state.json";state.write_text(json.dumps({"last_health_epoch":200000,
        "last_benchmark_epoch":200000}))
   scan=root/"scan.json"
   cmd=[sys.executable,"-I",str(dest/"runner.py"),"--config",str(cfg),
        "--state",str(state),"--scan-output",str(scan)]
   before=state.read_bytes()
   proc=subprocess.run(cmd,env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1]/"openwrt")},
       text=True,capture_output=True,timeout=8)
   self.assertEqual(proc.returncode,0,proc.stderr)
   self.assertEqual(json.loads(proc.stdout)["status"],"skipped")
   self.assertEqual(before,state.read_bytes())
   self.assertFalse(scan.exists())
   self.assertEqual(sorted(p.name for p in dest.glob("*.py")),
      sorted(p for p in json.loads((dest/"manifest.json").read_text())["files"]))
 def test_runner_direct_write_import_absent_in_bundled_process(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/"bundle";build(Path(__file__).resolve().parents[1]/"openwrt",dest)
   cmd=[sys.executable,"-I","-c",
     "import sys;sys.path.insert(0,sys.argv[1]);import runner;import rewrite_tx",
      str(dest)]
   proc=subprocess.run(cmd,cwd=d,text=True,capture_output=True,timeout=8,
      env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1]/"openwrt")})
   self.assertNotEqual(proc.returncode,0)
   self.assertIn("No module named 'rewrite_tx'",proc.stderr)
if __name__=="__main__":unittest.main()
