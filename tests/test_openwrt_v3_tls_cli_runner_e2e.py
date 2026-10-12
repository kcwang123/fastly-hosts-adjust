"""Real loopback TLS -> benchmark CLI -> persisted v3 -> runner E2E.

No internet, router, DNS mutation, or permanent certificate files.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import runner,https_benchmark
from settings import Settings

TARGET={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133",
        "candidate_ip":"151.101.1.133"}

@unittest.skipUnless(shutil.which("openssl"),"requires openssl for temporary test cert")
class EndToEnd(unittest.TestCase):
 def test_tls_cli_v3_runner_and_corrupt_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cert=root/"cert.pem";key=root/"key.pem"
   subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
       "-keyout",str(key),"-out",str(cert),"-subj","/CN=raw.githubusercontent.com",
       "-addext","subjectAltName=DNS:raw.githubusercontent.com"],check=True,
       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
   config={"benchmark_targets":[TARGET],"benchmark_sample_bytes":128,
           "benchmark_rounds":3,"max_benchmark_bytes":768,
           "max_sample_cv_percent":100.0,"benchmark_deadline_seconds":60,
           "dry_run":True,"auto_benchmark":False}
   cfg=root/"config.json";cfg.write_text(json.dumps(config))
   settings=Settings.load(cfg)
   serverctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
   serverctx.load_cert_chain(str(cert),str(key))
   clientctx=ssl.create_default_context(cafile=str(cert))
   listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(6)
   listener.settimeout(5);port=listener.getsockname()[1]
   observations=[];errors=[]
   def serve():
    try:
     for _ in range(6):
      conn,_=listener.accept()
      with serverctx.wrap_socket(conn,server_side=True) as tls:
       request=tls.recv(4096);observations.append(request)
       data=b"x"*128
       tls.sendall(b"HTTP/1.1 206 Partial Content\r\n"
        b"Content-Range: bytes 0-127/1024\r\nContent-Length: 128\r\n"
        b"ETag: \"fixture-v1\"\r\nX-Cache: HIT\r\nConnection: close\r\n\r\n"+data)
    except Exception as e: errors.append(e)
    finally:listener.close()
   thread=threading.Thread(target=serve,daemon=True);thread.start()
   original_connect=socket.create_connection
   def execute(cmd,**kwargs):
    try:
     arguments=cmd[cmd.index("--config"):]
     https_benchmark.main(arguments)
     return Mock(returncode=0)
    except Exception as e:
     errors.append(e)
     return Mock(returncode=1)
   state=root/"state.json";scan=root/"scan.json"
   with patch.object(https_benchmark.socket,"create_connection",
                     side_effect=lambda address,timeout:original_connect(("127.0.0.1",port),timeout)):
    with patch.object(https_benchmark.ssl,"create_default_context",return_value=clientctx):
     result=runner.run_once(settings,state,scan,100000,executor=execute,config_path=cfg)
   thread.join(5)
   self.assertFalse(thread.is_alive(),str(errors))
   self.assertFalse(errors,str(errors))
   self.assertEqual(result["status"],"ok",str(result))
   output=json.loads(Path(str(scan)+".benchmark.0.json").read_text())
   self.assertEqual(output["schema_version"],3)
   self.assertEqual(len(output["samples"]),6)
   self.assertEqual(output["diagnostics"]["etag"],'"fixture-v1"')
   self.assertTrue(all(b"Range: bytes=0-127" in item for item in observations))
   self.assertFalse(output["evidence"]["safe_to_apply"])
   from benchmark_v3 import verify
   mutated=json.loads(json.dumps(output))
   mutated["samples"][0]["etag"]='"tampered"'
   with self.assertRaises(ValueError):verify(mutated,settings,expected_target=TARGET)
if __name__=="__main__":unittest.main()
