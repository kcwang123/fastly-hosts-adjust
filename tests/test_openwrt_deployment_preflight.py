"""Read-only preflight contract tests; never execute checks on an actual router."""
from pathlib import Path
import subprocess
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"openwrt"/"deployment_preflight.sh"

class DeploymentPreflightTests(unittest.TestCase):
    def test_busybox_shell_syntax(self):
        subprocess.run(["sh","-n",str(SCRIPT)],check=True)
    def test_no_mutation_or_service_restart(self):
        source=SCRIPT.read_text()
        for forbidden in ("uci set ", "uci commit", "/etc/init.d/","service restart",
                          "opkg install", "crontab -", "iptables -", "nft add",
                          "rewrite/add","rewrite/delete", "sed -i", "rm -rf"):
            self.assertNotIn(forbidden,source)
        for required in ('check "AdGuard DNS listener 53"',
                         'check "DHCP listener 67"',
                         'check "dnsmasq port 54"',
                         'check "Python standard modules"',
                         'check "overlay >=10MiB available"'):
            self.assertIn(required,source)
if __name__=="__main__":unittest.main()
