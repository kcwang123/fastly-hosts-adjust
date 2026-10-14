"""Static hook and authorization contract. Not device-side hook execution."""
import pathlib
import re
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class HookContract(unittest.TestCase):
    def test_packages_do_not_define_automatic_script_restarts(self):
        for name in ("cdn-optimizer","luci-app-cdn-optimizer"):
            t=(ROOT/"openwrt"/name/"Makefile").read_text()
            self.assertNotIn("define Package/"+name+"/postinst",t)
            self.assertNotIn("define Package/"+name+"/prerm",t)
            for forbidden in ("uci commit","/etc/init.d/rpcd restart","/etc/init.d/uhttpd restart","reboot"):
                self.assertNotIn(forbidden,t)
    def test_generated_hooks_are_explicitly_inspected_in_sdk_ci(self):
        t=(ROOT/".github/workflows/openwrt-sdk-ipk.yml").read_text()
        self.assertIn("unpack/control/postinst",t)
        self.assertIn("unpack/control/prerm",t)
        self.assertIn("unpack-luci/control/postinst",t)
        self.assertIn("unpack-luci/control/prerm",t)
    def test_transaction_does_not_claim_automatic_rollback(self):
        t=(ROOT/"tools/test_real_opkg_transaction.sh").read_text()
        for marker in ("INJECT_PARTIAL_UPGRADE_DETECTED_BLOCK_OPERATOR_RECOVERY","INJECT_MISSING_SNAPSHOT_BLOCK_BEFORE_DOWNGRADE","INJECT_TAMPERED_SNAPSHOT_HASH_BLOCK_BEFORE_DOWNGRADE","ROLLBACK_EXPLICIT_CONFIG_RESTORE_VERIFIED"):
            self.assertIn(marker,t)
if __name__=="__main__":
    unittest.main()
