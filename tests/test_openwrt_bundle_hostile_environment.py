"""Hostile Python/TLS environment must not contaminate bundled launcher."""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from build_readonly_bundle import build,verify

class HostileEnvironment(unittest.TestCase):
 def test_launcher_ignores_python_and_ca_poisoning(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);artifact=root/"readonly";build(Path(__file__).resolve().parents[1]/"openwrt",artifact)
   poison=root/"poison";poison.mkdir()
   marker=root/"poison-ran"
   (poison/"sitecustomize.py").write_text("from pathlib import Path;Path("+repr(str(marker))+").write_text('injected')\n")
   (poison/"settings.py").write_text("raise RuntimeError('poisoned settings')\n")
   config=root/"config.json";config.write_text(json.dumps({"dry_run":True,"auto_benchmark":False}))
   state=root/"state.json";state.write_text(json.dumps({"last_health_epoch":int(time.time()),
       "last_benchmark_epoch":int(time.time())}))
   scan=root/"scan.json"
   env={**os.environ,"PYTHONPATH":str(poison),"PYTHONHOME":str(poison),
        "SSL_CERT_FILE":str(poison/"attacker.pem"),
        "REQUESTS_CA_BUNDLE":str(poison/"attacker.pem"),
        "CURL_CA_BUNDLE":str(poison/"attacker.pem")}
   cmd=[sys.executable,"-I","-B",str(artifact/"readonly_launcher.py"),
        "--config",str(config),"--state",str(state),"--scan-output",str(scan)]
   proc=subprocess.run(cmd,env=env,cwd=d,capture_output=True,text=True,timeout=8)
   self.assertEqual(proc.returncode,0,proc.stderr)
   self.assertEqual(json.loads(proc.stdout)["status"],"skipped")
   self.assertFalse(marker.exists())
   self.assertFalse(scan.exists())
   self.assertTrue(verify(artifact))
 def test_launcher_does_not_import_dns_writer(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/"readonly";build(Path(__file__).resolve().parents[1]/"openwrt",dest)
   self.assertFalse((dest/"rewrite_tx.py").exists())
   self.assertFalse((dest/"adguard_api.py").exists())
if __name__=="__main__":unittest.main()
