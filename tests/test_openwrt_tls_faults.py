"""Isolated real-TLS negative-path tests; only loopback sockets are used."""
import importlib.util
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("benchmark_tls_faults",root/"https_benchmark.py")
benchmark=importlib.util.module_from_spec(spec);sys.modules[spec.name]=benchmark;spec.loader.exec_module(benchmark)

@unittest.skipUnless(shutil.which("openssl"),"openssl needed for isolated TLS server test")
class RealTLSFaultTests(unittest.TestCase):
    def invoke(self, *, wrong_cert=False, slow=False, limit=64, deadline=None):
        with tempfile.TemporaryDirectory() as d:
            cert=Path(d)/"cert.pem"; key=Path(d)/"key.pem"
            name="untrusted.example" if wrong_cert else "raw.githubusercontent.com"
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
                "-keyout",str(key),"-out",str(cert),"-subj","/CN="+name,
                "-addext","subjectAltName=DNS:"+name],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert),str(key))
            trust=ssl.create_default_context(cafile=str(cert))
            listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
            listener.settimeout(3)
            port=listener.getsockname()[1]
            def serve():
                try:
                    conn,_=listener.accept()
                    try:
                        with context.wrap_socket(conn,server_side=True) as tls:
                            tls.recv(4096)
                            if slow: time.sleep(0.3)
                            tls.sendall(b"HTTP/1.1 206 Partial Content\\r\\nContent-Length: 64\\r\\n"
                                        b"Connection: close\\r\\n\\r\\n"+b"x"*64)
                    except (OSError,ssl.SSLError):
                        pass
                finally:
                    listener.close()
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            real_connect=socket.create_connection
            try:
                with patch.object(benchmark.socket,"create_connection",
                                  side_effect=lambda addr,timeout:real_connect(("127.0.0.1",port),timeout)):
                    with patch.object(benchmark.ssl,"create_default_context",return_value=trust):
                        return benchmark.download("raw.githubusercontent.com","151.101.1.133",
                                                  limit,2,0.1 if slow else 2,deadline=deadline)
            finally:
                thread.join(3)
                self.assertFalse(thread.is_alive())
    def test_wrong_certificate_rejected(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.invoke(wrong_cert=True)
    def test_slow_response_times_out(self):
        with self.assertRaises((TimeoutError,socket.timeout)):
            self.invoke(slow=True)
    def test_range_limit_with_real_tls(self):
        result=self.invoke(limit=64)
        self.assertEqual(result["bytes"],64)

if __name__=="__main__":unittest.main()
