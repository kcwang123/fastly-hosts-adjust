"""Two real child processes with local TLS: both targets and aggregate budget."""
import json,os,shutil,socket,ssl,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner
from settings import Settings

TARGETS=(
 {"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"},
 {"domain":"static-cdn.jtvnw.net","baseline_ip":"151.101.2.214","candidate_ip":"151.101.1.214"},
)
@unittest.skipUnless(shutil.which("openssl"),"requires temporary openssl test certificate")
class MultiProcessTLS(unittest.TestCase):
 def test_two_targets_twelve_tls_requests_one_success_timestamp(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);cert=p/"cert.pem";key=p/"key.pem"
   subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
    "-keyout",str(key),"-out",str(cert),"-subj","/CN=raw.githubusercontent.com",
    "-addext","subjectAltName=DNS:raw.githubusercontent.com,DNS:static-cdn.jtvnw.net"],
    check=True,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cert),str(key))
   sock=socket.socket();sock.bind(("127.0.0.1",0));sock.listen(12);sock.settimeout(8)
   port=sock.getsockname()[1];failures=[];domains=[]
   def serve():
    try:
     for _ in range(12):
      conn,_=sock.accept()
      with ctx.wrap_socket(conn,server_side=True) as tls:
       req=tls.recv(4096)
       if b"Range: bytes=0-127" not in req:raise AssertionError("wrong Range")
       domains.append(req)
       tls.sendall(b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 0-127/1024\r\n'
        b'Content-Length: 128\r\nETag: "same-v1"\r\nX-Cache: HIT\r\nConnection: close\r\n\r\n'+b"x"*128)
    except Exception as exc:failures.append(str(exc))
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
    "max_sample_cv_percent":100.0,"dry_run":True,"auto_benchmark":False}))
   state=p/"state.json";scan=p/"scan.json";settings=Settings.load(cfg)
   env={**os.environ,"PYTHONPATH":str(p),"SSL_CERT_FILE":str(cert)}
   with patch.dict(os.environ,env,clear=True):
    result=runner.run_once(settings,state,scan,100000,config_path=cfg)
   thread.join(8)
   self.assertFalse(thread.is_alive(),str(failures))
   self.assertFalse(failures,str(failures))
   self.assertEqual(result["status"],"ok",str(result))
   self.assertEqual(result["targets"],2)
   self.assertEqual(len(domains),12)
   for i in range(2):
    envelope=json.loads(Path(str(scan)+".benchmark."+str(i)+".json").read_text())
    self.assertEqual(len(envelope["samples"]),6)
    self.assertEqual(envelope["evidence"]["bytes_downloaded"],768)
    self.assertFalse(envelope["evidence"]["safe_to_apply"])
   self.assertEqual(runner.read_state(state),{"last_benchmark_epoch":100000})
 def test_second_target_truncated_http_never_updates_state(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);cert=p/"cert.pem";key=p/"key.pem"
   subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
    "-keyout",str(key),"-out",str(cert),"-subj","/CN=raw.githubusercontent.com",
    "-addext","subjectAltName=DNS:raw.githubusercontent.com,DNS:static-cdn.jtvnw.net"],
    check=True,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cert),str(key))
   sock=socket.socket();sock.bind(("127.0.0.1",0));sock.listen(12);sock.settimeout(8)
   port=sock.getsockname()[1];failures=[];domains=[]
   def serve():
    try:
     for _ in range(7):
      conn,_=sock.accept()
      with ctx.wrap_socket(conn,server_side=True) as tls:
       req=tls.recv(4096)
       if b"Range: bytes=0-127" not in req:raise AssertionError("wrong Range")
       if len(domains)>=6:
        tls.sendall(b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 0-127/1024\r\nContent-Length: 128\r\nConnection: close\r\n\r\n'+b'x'*24)
        domains.append(req)
        continue
       domains.append(req)
       tls.sendall(b'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes 0-127/1024\r\n'
        b'Content-Length: 128\r\nETag: "same-v1"\r\nX-Cache: HIT\r\nConnection: close\r\n\r\n'+b"x"*128)
    except Exception as exc:failures.append(str(exc))
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
    "max_sample_cv_percent":100.0,"dry_run":True,"auto_benchmark":False}))
   state=p/"state.json";scan=p/"scan.json";settings=Settings.load(cfg)
   env={**os.environ,"PYTHONPATH":str(p),"SSL_CERT_FILE":str(cert)}
   with patch.dict(os.environ,env,clear=True):
    result=runner.run_once(settings,state,scan,100000,config_path=cfg)
   thread.join(8)
   self.assertFalse(thread.is_alive(),str(failures))
   self.assertFalse(failures,str(failures))
   self.assertEqual(result["status"],"error",str(result))
   self.assertGreaterEqual(len(domains),7)
   self.assertFalse(state.exists())
   first=json.loads(Path(str(scan)+".benchmark.0.json").read_text())
   self.assertEqual(first["schema_version"],3)
if __name__=="__main__":unittest.main()
