"""Real loopback TLS server test, using ephemeral local self-signed certificate.

No public network, router, or permanent certificate writes. Openssl is used
only for temporary test fixtures, never as a runtime dependency.
"""
import importlib.util
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("benchmark_tls_local",root/"https_benchmark.py")
benchmark=importlib.util.module_from_spec(spec);sys.modules[spec.name]=benchmark;spec.loader.exec_module(benchmark)


@unittest.skipUnless(shutil.which("openssl"),"openssl required for ephemeral TLS fixture")
class LocalTLSTests(unittest.TestCase):
    def test_local_tls_truncated_body_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            cert=Path(d)/"cert.pem"; key=Path(d)/"key.pem"
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes",
                "-days","1","-keyout",str(key),"-out",str(cert),
                "-subj","/CN=raw.githubusercontent.com",
                "-addext","subjectAltName=DNS:raw.githubusercontent.com"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
            server=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server.load_cert_chain(str(cert),str(key))
            client=ssl.create_default_context(cafile=str(cert))
            listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
            port=listener.getsockname()[1]
            def serve():
                try:
                    conn,_=listener.accept()
                    with server.wrap_socket(conn,server_side=True) as tls:
                        tls.recv(4096)
                        tls.sendall(b"HTTP/1.1 206 Partial Content\r\nContent-Length: 32\r\nContent-Range: bytes 0-255/256\r\n"
                                    b"Connection: close\r\n\r\n"+b"x"*32)
                finally:
                    listener.close()
            worker=threading.Thread(target=serve,daemon=True);worker.start()
            real_connect=socket.create_connection
            with patch.object(benchmark.socket,"create_connection",
                              side_effect=lambda addr,timeout:real_connect(("127.0.0.1",port),timeout)):
                with patch.object(benchmark.ssl,"create_default_context",return_value=client):
                    with self.assertRaisesRegex(ValueError,"too small"):
                        benchmark.download("raw.githubusercontent.com","151.101.1.133",256,2,2)
            worker.join(3)
            self.assertFalse(worker.is_alive())
    def test_real_tls_sni_range_and_truncated_file(self):
        with tempfile.TemporaryDirectory() as d:
            cert=Path(d)/"cert.pem";key=Path(d)/"key.pem"
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes",
                "-days","1","-keyout",str(key),"-out",str(cert),
                "-subj","/CN=raw.githubusercontent.com",
                "-addext","subjectAltName=DNS:raw.githubusercontent.com"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
            server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.load_cert_chain(str(cert),str(key))
            client_context=ssl.create_default_context(cafile=str(cert))
            observed=[]
            ready=threading.Event()
            listener=socket.socket()
            listener.bind(("127.0.0.1",0));listener.listen(1)
            port=listener.getsockname()[1]
            def serve():
                ready.set()
                try:
                    conn,_=listener.accept()
                    with server_context.wrap_socket(conn,server_side=True) as secure:
                        request=secure.recv(4096)
                        observed.append(request)
                        data=b"x"*256
                        secure.sendall(b"HTTP/1.1 206 Partial Content\r\nContent-Length: 256\r\nContent-Range: bytes 0-255/256\r\n"
                                       b"Connection: close\r\n\r\n"+data)
                finally:
                    listener.close()
            thread=threading.Thread(target=serve,daemon=True)
            thread.start();self.assertTrue(ready.wait(2))
            original_connect=socket.create_connection
            with patch.object(benchmark.socket,"create_connection",
                              side_effect=lambda address,timeout:original_connect(("127.0.0.1",port),timeout)):
                with patch.object(benchmark.ssl,"create_default_context",return_value=client_context):
                    result=benchmark.download("raw.githubusercontent.com","151.101.1.133",256,3,3)
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result["bytes"],256)
            self.assertIn(b"Range: bytes=0-255",observed[0])
            self.assertIn(b"Host: raw.githubusercontent.com",observed[0])
if __name__=="__main__":unittest.main()
