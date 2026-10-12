import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import urllib.error

p=Path(__file__).resolve().parents[1]/"openwrt"/"adguard_api.py"
spec=importlib.util.spec_from_file_location("adguard_api",p)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

class Response:
    status=200
    def __init__(self,body): self.body=body
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,limit): return self.body

class APITests(unittest.TestCase):
    def test_local_only(self):
        for url in ("https://127.0.0.1:3000","http://192.168.1.240:3000",
                    "http://127.0.0.1:3000/x","http://user:pass@localhost:3000",
                    "http://localhost:3000/?x=y"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                mod.AdGuardAPI(url,"u","p")

    def test_list_add_delete_contract(self):
        seen=[]
        def opener(req,timeout):
            seen.append((req.full_url,req.get_method(),req.data,timeout,req.get_header("Authorization")))
            return Response(b'[{"domain":"raw.githubusercontent.com","answer":"151.101.1.133"}]' if req.get_method()=="GET" else b'')
        api=mod.AdGuardAPI("http://127.0.0.1:3000","user","secret",3,opener)
        self.assertEqual(len(api.list()),1)
        api.add("raw.githubusercontent.com","151.101.1.133")
        api.delete("raw.githubusercontent.com","151.101.1.133")
        self.assertEqual([x[1] for x in seen],["GET","POST","POST"])
        self.assertEqual(json.loads(seen[1][2])["answer"],"151.101.1.133")
        self.assertEqual(seen[1][3],3)
        self.assertTrue(seen[0][4].startswith("Basic "))
        self.assertNotIn("secret",str(seen))

    def test_http_failure_no_credentials(self):
        def opener(req,timeout): raise urllib.error.HTTPError(req.full_url,403,"denied",None,None)
        api=mod.AdGuardAPI("http://localhost:3000","admin","verysecret",opener=opener)
        with self.assertRaisesRegex(RuntimeError,"HTTP 403") as ctx:
            api.list()
        self.assertNotIn("verysecret",str(ctx.exception))
if __name__=="__main__":unittest.main()
