import importlib.util
import pathlib
import unittest
from unittest.mock import patch, MagicMock

p = pathlib.Path(__file__).resolve().parents[1] / "openwrt" / "tls_verify.py"
s = importlib.util.spec_from_file_location("tls_verify", p)
m = importlib.util.module_from_spec(s)
import sys
sys.modules[s.name] = m
s.loader.exec_module(m)

class TLSVerifyTests(unittest.TestCase):
    def test_reject_unknown_domain_and_local_ip(self):
        for domain, ip in [("example.com","151.101.1.133"),
                           ("raw.githubusercontent.com","127.0.0.1")]:
            with self.assertRaises(ValueError):
                m.verify(domain,ip)

    @patch.object(m.http.client, "HTTPResponse")
    @patch.object(m.ssl, "create_default_context")
    @patch.object(m.socket, "create_connection")
    def test_sni_and_request_host(self, connect, context, response):
        tls=MagicMock()
        context.return_value.wrap_socket.return_value=tls
        response.return_value.status=200
        outcome=m.verify("raw.githubusercontent.com","151.101.1.133", 3.0)
        self.assertTrue(outcome.verified)
        self.assertEqual(context.return_value.wrap_socket.call_args.kwargs["server_hostname"],
                         "raw.githubusercontent.com")
        sent=tls.sendall.call_args.args[0]
        self.assertIn(b"Host: raw.githubusercontent.com", sent)
        connect.assert_called_once_with(("151.101.1.133",443),timeout=3.0)

    @patch.object(m.socket, "create_connection",side_effect=OSError("unreachable"))
    def test_connection_failure(self, connect):
        self.assertFalse(m.verify("pbs.twimg.com","151.101.1.159").verified)

if __name__ == "__main__":
    unittest.main()
