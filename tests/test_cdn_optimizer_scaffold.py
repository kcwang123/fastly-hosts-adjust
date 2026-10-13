import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CDN = ROOT / "openwrt" / "cdn-optimizer"
LUCI = ROOT / "openwrt" / "luci-app-cdn-optimizer"


class OfflinePackagingContract(unittest.TestCase):
    def test_rpc_acl_is_read_only_and_path_scoped(self):
        path = CDN / "files/usr/share/rpcd/acl.d/luci-app-cdn-optimizer.json"
        acl = json.loads(path.read_text())
        rule = acl["luci-app-cdn-optimizer"]
        self.assertNotIn("write", rule)
        self.assertEqual(rule["read"]["file"], {"/tmp/cdn-optimizer/result.json": ["read"]})
        self.assertNotIn("exec", str(rule).lower())

    def test_disabled_by_default(self):
        config = (CDN / "files/etc/config/cdn_optimizer").read_text()
        self.assertIn("option enabled '0'", config)
        self.assertIn("option allow_public_probe '0'", config)
        init = (CDN / "files/etc/init.d/cdn-optimizer").read_text()
        self.assertNotIn("procd_set_param command", init)
        self.assertNotIn("fastly-public-health", init)

    def test_menu_view_is_read_only(self):
        menu = json.loads((LUCI / "root/usr/share/luci/menu.d/luci-app-cdn-optimizer.json").read_text())
        self.assertEqual(menu["admin/services/cdn-optimizer"]["action"]["path"], "cdn-optimizer/overview")
        code = (LUCI / "htdocs/luci-static/resources/view/cdn-optimizer/overview.js").read_text()
        self.assertIn("fs.read('/tmp/cdn-optimizer/result.json')", code)
        self.assertNotIn("fs.exec", code)
        self.assertNotIn("fs.write", code)
        self.assertNotIn("uci.set", code)
        self.assertNotIn("rpc.declare", code)

    def test_package_is_explicitly_passive(self):
        makefile = (CDN / "Makefile").read_text()
        self.assertNotIn("Build/Compile\n\tgo", makefile)
        self.assertIn("PKG_NAME:=cdn-optimizer", makefile)
        self.assertNotIn("uci commit", makefile)


if __name__ == "__main__":
    unittest.main()
