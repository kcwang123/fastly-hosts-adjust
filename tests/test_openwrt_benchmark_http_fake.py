"""Protocol-level HTTP fake for bounded TLS download. No network required."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("bench_http_fake",root/"https_benchmark.py")
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

class FakeHTTP:
    status=200
    def __init__(self, sock):
        self.sock=sock
        self.count=0
    def begin(self):pass
    def read(self,n):
        self.count+=n
        return b"x"*n

class FakeServerTests(unittest.TestCase):
    @patch.object(mod.http.client,"HTTPResponse",FakeHTTP)
    @patch.object(mod.ssl,"create_default_context")
    @patch.object(mod.socket,"create_connection")
    def test_range_cap_and_hostname_sni(self,connect,context):
        tls=MagicMock()
        context.return_value.wrap_socket.return_value=tls
        result=mod.download("raw.githubusercontent.com","151.101.1.133",1000,2,3)
        self.assertEqual(result["bytes"],1000)
        self.assertEqual(result["status"],200)
        self.assertEqual(context.return_value.wrap_socket.call_args.kwargs["server_hostname"],"raw.githubusercontent.com")
        request=tls.sendall.call_args.args[0]
        self.assertIn(b"Range: bytes=0-999",request)
        self.assertIn(b"Host: raw.githubusercontent.com",request)
    @patch.object(mod.http.client,"HTTPResponse")
    @patch.object(mod.ssl,"create_default_context")
    @patch.object(mod.socket,"create_connection")
    def test_tiny_file_rejected(self,connect,context,response):
        tls=MagicMock()
        context.return_value.wrap_socket.return_value=tls
        instance=response.return_value
        instance.status=200
        instance.read.side_effect=[b"tiny",b""]
        with self.assertRaisesRegex(ValueError,"too small"):
            mod.download("raw.githubusercontent.com","151.101.1.133",4096,2,3)
    @patch.object(mod.socket,"create_connection",side_effect=TimeoutError("timeout"))
    def test_connect_timeout_aborts(self,connect):
        with self.assertRaises(TimeoutError):
            mod.download("raw.githubusercontent.com","151.101.1.133",500,2,3)
    def test_deadline_before_connection(self):
        with patch.object(mod.time,"monotonic",return_value=100):
            with self.assertRaises(TimeoutError):
                mod.download("raw.githubusercontent.com","151.101.1.133",500,2,3,deadline=99)
if __name__=="__main__":unittest.main()
