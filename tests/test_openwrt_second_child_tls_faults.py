"""Second child must fail closed on certificate rejection or read timeout.
First child performs six real verified loopback TLS downloads; no public traffic.
"""
import json,os,shutil,socket,ssl,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings
TARGETS=(
 {"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"},
 {"domain":"static-cdn.jtvnw.net","baseline_ip":"151.101.2.214","candidate_ip":"151.101.1.214"})
@unittest.skipUnless(shutil.which("openssl"),"requires openssl")
class SecondChildFault(unittest.TestCase):
 def exercise(self,mode):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);cert=p/"cert.pem";key=p/"key.pem"
   alt="DNS:raw.githubusercontent.com,DNS:static-cdn.jtvnw.net" if mode=="timeout" else "DNS:raw.githubusercontent.com"
   subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
    "-keyout",str(key),"-out",str(cert),"-subj","/CN=raw.githubusercontent.com",
    "-addext","subjectAltName="+alt],check=True,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cert),str(key))
   sock=socket.socket();sock.bind(("127.0.0.1",0));sock.listen(7);sock.settimeout(7)
   port=sock.getsockname()[1];failures=[];seen=[]
   def serve():
    try:
     for i in range(7):
      conn,_=sock.accept()
      try:
       with ctx.wrap_socket(conn,server_side=True) as tls:
        seen.append(i)
        tls.recv(4096)
        if i==6 and mode=="timeout":
         time.sleep(0.4)
        else:
         tls.sendall(b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 0-127/1024\r\n'
           b'Content-Length: 128\r\nETag: "v1"\r\nX-Cache: HIT\r\nConnection: close\r\n\r\n'+b'x'*128)
      except ssl.SSLError:
       if mode!="certificate":raise
    except Exception as exc:failures.append(repr(exc))
    finally:sock.close()
   thread=threading.Thread(target=serve,daemon=True);thread.start()
   (p/"sitecustomize.py").write_text(
    "import socket\n_orig=socket.create_connection\n"
    "def redirect(addr,timeout=socket._GLOBAL_DEFAULT_TIMEOUT,source_address=None,*,all_errors=False):\n"
    "    if addr[1]!=443: raise RuntimeError('non-test port')\n"
    "    return _orig(('127.0.0.1',"+str(port)+"),timeout)\n"
    "socket.create_connection=redirect\n")
   cfg=p/"config.json";cfg.write_text(json.dumps({"benchmark_targets":TARGETS,
    "benchmark_sample_bytes":128,"benchmark_rounds":3,"max_benchmark_bytes":1536,
    "benchmark_read_timeout_seconds":0.1,"benchmark_deadline_seconds":5,"process_timeout_seconds":10,
    "max_sample_cv_percent":100.0,"dry_run":True,"auto_benchmark":False}))
   settings=Settings.load(cfg);state=p/"state.json";scan=p/"scan.json"
   runner.atomic_json(state,{"last_health_epoch":10,"last_benchmark_epoch":20})
   stale=Path(str(scan)+".benchmark.1.json");stale.write_text('{"fake":"old"}')
   with patch.dict(os.environ,{**os.environ,"PYTHONPATH":str(p),"SSL_CERT_FILE":str(cert)},clear=True):
    result=runner.run_once(settings,state,scan,100000,config_path=cfg)
   thread.join(7)
   self.assertFalse(thread.is_alive(),str(failures))
   self.assertFalse(failures,str(failures))
   self.assertEqual(result["status"],"error",str(result))
   self.assertEqual(runner.read_state(state),{"last_health_epoch":10,"last_benchmark_epoch":20})
   self.assertGreaterEqual(len(seen),6)
   self.assertTrue(Path(str(scan)+".benchmark.0.json").exists())
   self.assertFalse(stale.exists())
 def test_certificate_error(self):self.exercise("certificate")
 def test_read_timeout(self):self.exercise("timeout")
if __name__=="__main__":unittest.main()
