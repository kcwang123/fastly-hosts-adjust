"""Offline adversarial tests for the OpenWrt rpcd read-only JSON responder.

The harness substitutes only offline paths and command shims. It never invokes a
router or public endpoint. Owner checks are mocked because CI is non-root.
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "openwrt/cdn-optimizer/files/usr/libexec/rpcd/cdn-optimizer"


class RpcdHostileFixtures(unittest.TestCase):
    def test_fixtures(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            state = base / "state"
            state.mkdir(mode=0o700)
            output = state / "result.json"
            binpath = base / "bin"
            binpath.mkdir()
            real_ls = subprocess.check_output(["which", "ls"], text=True).strip()
            real_cat = subprocess.check_output(["which", "cat"], text=True).strip()
            real_wc = subprocess.check_output(["which", "wc"], text=True).strip()
            # Use explicit executable shims: no router, no superuser needed.
            (binpath / "ls").write_text(
                "#!/bin/sh\n"
                "if [ \"$3\" = \""+str(state)+"\" ]; then echo 'drwx------ 2 0 0 60 Jan 1 00:00 state'; "
                "else echo \"-rw------- 1 0 0 100 Jan 1 00:00 result.json\"; fi\n"
            )
            (binpath / "jsonfilter").write_text(
                "#!/usr/bin/env python3\n"
                "import json,sys\n"
                "a=sys.argv\n"
                "try:\n"
                "  p=a[a.index('-s')+1]; field=a[a.index('-e')+1][2:]\n"
                "  def unique(pairs):\n"
                "    d={}\n"
                "    for k,v in pairs:\n"
                "      if k in d: raise ValueError('duplicate')\n"
                "      d[k]=v\n"
                "    return d\n"
                "  v=json.loads(p,object_pairs_hook=unique)[field]\n"
                "  print(str(v).lower() if isinstance(v,bool) else v)\n"
                "except Exception: sys.exit(1)\n"
            )
            # Provide only the known utilities needed by the plugin.
            for name, target in [("cat",real_cat),("wc",real_wc)]:
                (binpath / name).symlink_to(target)
            for x in [binpath / "ls",binpath / "jsonfilter"]:
                x.chmod(0o755)
            source=PLUGIN.read_text().replace(
                "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                "PATH="+str(binpath)+":/usr/bin:/bin"
            ).replace("state=/tmp/cdn-optimizer","state="+str(state)).replace(
                "result=/tmp/cdn-optimizer/result.json","result="+str(output))
            temp_script=base/"plugin"
            temp_script.write_text(source)
            temp_script.chmod(0o755)
            good={"schema_version":1,"mode":"read_only","network_executed":True,
                  "safe_to_apply":False,"service":"github","result":{"tls_verified":True}}
            fallback={"schema_version":1,"status":"not_tested","safe_to_apply":False}
            def call():
                result=subprocess.run(["sh",str(temp_script),"call","status"],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            output.write_text(json.dumps(good));output.chmod(0o600)
            self.assertEqual(call(),good)
            for payload in ["{", "{}", json.dumps({**good,"safe_to_apply":True}),
                            json.dumps({**good,"schema_version":2}),
                            json.dumps({**good,"mode":"apply"}),
                            json.dumps(good)+"x", "x"*16385,
                            '{"schema_version":1,"schema_version":2,"safe_to_apply":false,"mode":"read_only"}']:
                with self.subTest(payload=payload[:60]):
                    output.write_text(payload);output.chmod(0o600)
                    self.assertEqual(call(),fallback)
            output.unlink()
            output.symlink_to(base/"outside.json")
            self.assertEqual(call(),fallback)
            output.unlink()
            output.write_text(json.dumps(good));output.chmod(0o600)
            (binpath/"jsonfilter").rename(binpath/"jsonfilter-removed")
            self.assertEqual(call(),fallback)


if __name__=="__main__":
    unittest.main()
