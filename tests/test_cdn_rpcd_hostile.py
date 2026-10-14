"""Offline hostile-fixture smoke for restricted rpcd status; no router I/O."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "openwrt/cdn-optimizer/files/usr/libexec/rpcd/cdn-optimizer"
FALLBACK = {"schema_version": 1, "status": "not_tested", "safe_to_apply": False}


class RpcdHostileFixtureTests(unittest.TestCase):
    def test_hostile_results_fail_closed_and_good_result_survives(self):
        # Filesystem owner is the running uid in this offline harness. Replace only
        # the script's numeric root comparison, never change the production script.
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            state = base / "state"
            state.mkdir(mode=0o700)
            result = state / "result.json"
            tool = base / "bin"
            tool.mkdir()
            mock = tool / "jsonfilter"
            mock.write_text("""#!/usr/bin/env python3
import json,sys
args=sys.argv[1:]
try:
    source=args[args.index('-s')+1]
    field=args[args.index('-e')+1].removeprefix('@.')
    def no_dups(pairs):
        obj={}
        for key,val in pairs:
            if key in obj: raise ValueError('duplicate key')
            obj[key]=val
        return obj
    data=json.loads(source,object_pairs_hook=no_dups)
    val=data[field]
    print('true' if val is True else 'false' if val is False else str(val))
except Exception:
    sys.exit(1)
""")
            mock.chmod(0o755)
            source = SOURCE.read_text()
            source = source.replace("PATH=/usr/sbin:/usr/bin:/sbin:/bin", f"PATH={tool}:/usr/sbin:/usr/bin:/sbin:/bin")
            source = source.replace("state=/tmp/cdn-optimizer", f"state={state}")
            source = source.replace("result=/tmp/cdn-optimizer/result.json", f"result={result}")
            source = source.replace('"$3" = 0 ] && [ "$4" = 0', f'"$3" = {os.getuid()} ] && [ "$4" = {os.getgid()}')
            plugin=base / "rpcd"
            plugin.write_text(source)
            plugin.chmod(0o755)

            def invoke():
                run=subprocess.run(["sh", str(plugin), "call", "status"], capture_output=True, text=True, timeout=3)
                self.assertEqual(run.returncode,0,run.stderr)
                return json.loads(run.stdout)

            valid={"schema_version":1,"mode":"read_only","network_executed":True,"safe_to_apply":False,"service":"github"}
            result.write_text(json.dumps(valid))
            result.chmod(0o600)
            self.assertEqual(invoke(),valid)
            for payload in (
                "{broken", '{"schema_version":2,"mode":"read_only","safe_to_apply":false}',
                '{"schema_version":1,"mode":"write","safe_to_apply":false}',
                '{"schema_version":1,"mode":"read_only","safe_to_apply":true}',
                '{"schema_version":1,"schema_version":2,"mode":"read_only","safe_to_apply":false}',
                "{}",
            ):
                result.write_text(payload)
                result.chmod(0o600)
                self.assertEqual(invoke(),FALLBACK)
            result.write_text(json.dumps(valid))
            result.chmod(0o644)
            self.assertEqual(invoke(),FALLBACK)
            result.chmod(0o600)
            result.write_text("X" * 16385)
            self.assertEqual(invoke(),FALLBACK)
            result.unlink()
            result.symlink_to(plugin)
            self.assertEqual(invoke(),FALLBACK)
            result.unlink()
            result.write_text(json.dumps(valid))
            result.chmod(0o600)
            state.chmod(0o755)
            self.assertEqual(invoke(),FALLBACK)


if __name__ == "__main__":
    unittest.main()
