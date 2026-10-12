"""Run the preflight against fake OpenWrt commands and fixture paths."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"openwrt"/"deployment_preflight.sh"

class MockPreflightExecution(unittest.TestCase):
    def test_passes_and_fails_against_fake_read_only_services(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bin_dir=root/"bin";bin_dir.mkdir()
            release=root/"openwrt_release";release.write_text("DISTRIB_ID='OpenWrt'\n")
            agh=root/"adguardhome.yaml";agh.write_text("dns:\n  port: 53\n")
            for name, body in {
                "netstat": 'echo "udp 0 0 0.0.0.0:53 0.0.0.0:*"; echo "udp 0 0 0.0.0.0:67 0.0.0.0:*"',
                "uci": 'echo "54"',
                "python3": 'exit 0',
                "df": 'printf "Filesystem 1K-blocks Used Available Use%% Mounted\\n/dev/root 100000 1000 99000 1%% /overlay\\n"',
            }.items():
                p=bin_dir/name;p.write_text("#!/bin/sh\n"+body+"\n");p.chmod(0o755)
            # Replace only absolute fixture paths in a temporary test copy.
            source=SCRIPT.read_text().replace("/etc/openwrt_release",str(release)).replace(
                "/etc/adguardhome.yaml",str(agh))
            copy=root/"preflight.sh";copy.write_text(source)
            env={**os.environ,"PATH":str(bin_dir)+":"+os.environ["PATH"]}
            ok=subprocess.run(["sh",str(copy)],env=env,capture_output=True,text=True)
            self.assertEqual(ok.returncode,0,ok.stdout+ok.stderr)
            self.assertIn("PASS DHCP listener 67",ok.stdout)
            (bin_dir/"uci").write_text("#!/bin/sh\necho 53\n")
            broken=subprocess.run(["sh",str(copy)],env=env,capture_output=True,text=True)
            self.assertNotEqual(broken.returncode,0)
            self.assertIn("FAIL dnsmasq port 54",broken.stdout)
if __name__=="__main__":unittest.main()
