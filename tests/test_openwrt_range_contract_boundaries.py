"""Contract boundary tests: reject invalid HTTP range/cache representations."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
import https_benchmark as bench

class RangeContractTests(unittest.TestCase):
    def sample(self, status=206, headers=None, body=b"x"*64):
        headers=headers or {"Content-Range":"bytes 0-63/128", "Content-Length":"64"}
        class FakeResponse:
            def __init__(self, sock): self.status=status; self.offset=0
            def begin(self): pass
            def getheader(self, key, default=None): return headers.get(key,default)
            def read(self,n):
                value=body[self.offset:self.offset+n]
                self.offset+=len(value)
                return value
        ssl_context=MagicMock()
        with patch.object(bench.socket,"create_connection",return_value=MagicMock()):
            with patch.object(bench.ssl,"create_default_context",return_value=ssl_context):
                with patch.object(bench.http.client,"HTTPResponse",FakeResponse):
                    return bench.download("raw.githubusercontent.com","151.101.1.133",64,2,2)
    def test_valid_partial_content(self):
        self.assertEqual(self.sample()["bytes"],64)
    def test_range_total_too_small(self):
        with self.assertRaisesRegex(ValueError,"Content-Range"):
            self.sample(headers={"Content-Range":"bytes 0-63/32","Content-Length":"64"})
    def test_wrong_range_start(self):
        with self.assertRaisesRegex(ValueError,"Content-Range"):
            self.sample(headers={"Content-Range":"bytes 1-64/128","Content-Length":"64"})
    def test_cache_no_store(self):
        with self.assertRaisesRegex(ValueError,"no-store"):
            self.sample(headers={"Content-Range":"bytes 0-63/128",
                                 "Content-Length":"64","Cache-Control":"private, no-store"})
    def test_content_encoding_gzip(self):
        with self.assertRaisesRegex(ValueError,"compressed"):
            self.sample(headers={"Content-Range":"bytes 0-63/128",
                                 "Content-Encoding":"gzip"})
    def test_content_length_truncated(self):
        with self.assertRaisesRegex(ValueError,"too small"):
            self.sample(body=b"x"*32)
    def test_status_200_rejected(self):
        with self.assertRaisesRegex(ValueError,"Range"):
            self.sample(status=200)
if __name__=="__main__": unittest.main()
