"""Reject changed/deleted/extra bundle files before any Runner work."""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build
SRC=Path(__file__).resolve().parents[1]/"openwrt"
class StartupIntegrity(unittest.TestCase):
 def test_invalid_artifact_denies_runner(self):
  for scenario in ("tamper","missing","extra","symlink","manifest_link"):
   with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as d:
    root=Path(d);dest=root/"bundle";build(SRC,dest)
    if scenario=="tamper":(dest/"runner.py").write_text("print('RUNNER SHOULD NOT RUN')\n")
    elif scenario=="missing":(dest/"settings.py").unlink()
    elif scenario=="extra":(dest/"rewrite_tx.py").write_text("pass\n")
    elif scenario=="symlink":
     (dest/"runner.py").unlink();(dest/"runner.py").symlink_to(SRC/"runner.py")
    else:
     original=(dest/"manifest.json").read_bytes();(dest/"manifest.json").unlink()
     (root/"outside.json").write_bytes(original);(dest/"manifest.json").symlink_to(root/"outside.json")
    cfg=root/"config.json";cfg.write_text(json.dumps({"dry_run":True,"auto_benchmark":False}))
    state=root/"state.json";state.write_text(json.dumps({"last_health_epoch":int(time.time()),
      "last_benchmark_epoch":int(time.time())}))
    before=state.read_bytes();scan=root/"scan.json"
    cmd=[sys.executable,"-I","-B",str(dest/"readonly_launcher.py"),
     "--config",str(cfg),"--state",str(state),"--scan-output",str(scan)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=10,cwd=d)
    self.assertNotEqual(p.returncode,0,p.stdout)
    self.assertNotIn("RUNNER SHOULD NOT RUN",p.stdout)
    self.assertEqual(state.read_bytes(),before)
    self.assertFalse(scan.exists())
if __name__=="__main__":unittest.main()
