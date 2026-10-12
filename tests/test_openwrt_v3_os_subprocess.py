"""OS-level HTTPS benchmark subprocess with loopback TLS, persisted v3, Runner gate.

sitecustomize is injected ONLY into child process via a temporary PYTHONPATH.
No router, public CDN, DNS mutation or privileged sockets involved.
"""
import json,os,shutil,socket,ssl,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings

TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133",
        "candidate_ip":"151.101.1.133"}
@unittest.skipUnless(shutil.which("openssl"),"requires openssl")
class SubprocessTLS(unittest.TestCase):
 def test_os_subprocess_evidence_roundtrip_and_stale_file(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);cert=p/"cert.pem";key=p/"key.pem"
   subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
    "-keyout",str(key),"-out",str(cert),"-subj","/CN=raw.githubusercontent.com",
    "-addext","subjectAltName=DNS:raw.githubusercontent.com"],
    check=True,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   server=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server.load_cert_chain(str(cert),str(key))
   listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(6)
   listener.settimeout(6);port=listener.getsockname()[1];failures=[]
   def serve():
    try:
     for _ in range(6):
      conn,_=listener.accept()
      with server.wrap_socket(conn,server_side=True) as tls:
       req=tls.recv(4096)
       if b"Range: bytes=0-127" not in req:raise AssertionError("Range missing")
       tls.sendall(b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 0-127/1024\r\n'
          b'Content-Length: 128\r\nETag: "same-v1"\r\nX-Cache: HIT\r\nConnection: close\r\n\r\n'+b"x"*128)
    except Exception as e:failures.append(str(e))
    finally:listener.close()
   thread=threading.Thread(target=serve,daemon=True);thread.start()
   # A child's sitecustomize modifies only its destination for test injection.
   (p/"sitecustomize.py").write_text(
       "import socket\n"
       "_connect=socket.create_connection\n"
       "def local_only(addr,timeout=socket._GLOBAL_DEFAULT_TIMEOUT,source_address=None,*,all_errors=False):\n"
       "    if addr[1]!=443: raise RuntimeError('unexpected test destination')\n"
       "    return _connect(('127.0.0.1',"+str(port)+"),timeout)\n"
       "socket.create_connection=local_only\n")
   cfg=p/"config.json";cfg.write_text(json.dumps({"benchmark_targets":[TARGET],
    "benchmark_sample_bytes":128,"benchmark_rounds":3,"max_benchmark_bytes":768,
    "max_sample_cv_percent":100.0,"dry_run":True,"auto_benchmark":False}))
   settings=Settings.load(cfg);state=p/"state.json";scan=p/"scan.json"
   old=Path(str(scan)+".benchmark.0.json")
   old.write_text('{"schema_version":3,"untrusted":true}')
   env={**os.environ,"PYTHONPATH":str(p),"SSL_CERT_FILE":str(cert)}
   with patch.dict(os.environ,env,clear=True):
    result=runner.run_once(settings,state,scan,100000,config_path=cfg)
   thread.join(6)
   self.assertFalse(thread.is_alive(),str(failures))
   self.assertFalse(failures,str(failures))
   self.assertEqual(result["status"],"ok",str(result))
   artifact=json.loads(old.read_text())
   self.assertEqual(artifact["schema_version"],3)
   self.assertEqual(len(artifact["samples"]),6)
   self.assertFalse(artifact["evidence"]["safe_to_apply"])
   self.assertNotIn("untrusted",artifact)
   self.assertEqual(runner.read_state(state)["last_benchmark_epoch"],100000)
if __name__=="__main__":unittest.main()
