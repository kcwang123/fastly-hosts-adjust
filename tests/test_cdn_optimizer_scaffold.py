import json
import pathlib
import subprocess
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
        self.assertEqual(rule["read"]["ubus"]["cdn-optimizer"], ["status"])
        self.assertNotIn("file", rule["read"])
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
        for page in ("overview", "results", "settings"):
            key = "admin/services/cdn-optimizer" + ("/" + page if page != "overview" else "")
            self.assertEqual(menu[key]["action"]["path"], "cdn-optimizer/" + page)
        code = (LUCI / "htdocs/luci-static/resources/view/cdn-optimizer/overview.js").read_text()
        self.assertIn("method: 'status'", code)
        self.assertIn("object: 'cdn-optimizer'", code)
        self.assertNotIn("fs.exec", code)
        self.assertNotIn("fs.write", code)
        self.assertNotIn("uci.set", code)
        self.assertIn("rpc.declare", code)
        for page in ("results", "settings"):
            script = (LUCI / "htdocs/luci-static/resources/view/cdn-optimizer" / (page + ".js")).read_text()
            self.assertNotIn("fs.exec", script)
            self.assertNotIn("uci.set", script)
            self.assertNotIn("fs.write", script)

    def test_package_is_explicitly_passive(self):
        makefile = (CDN / "Makefile").read_text()
        self.assertNotIn("Build/Compile\n\tgo", makefile)
        self.assertIn("PKG_NAME:=cdn-optimizer", makefile)
        self.assertIn("CDN_OPTIMIZER_BIN", makefile)
        self.assertIn("CDN_OPTIMIZER_SHA256", makefile)
        self.assertIn("sha256sum -c -", makefile)
        self.assertIn("$(INSTALL_BIN) $(CDN_OPTIMIZER_BIN)", makefile)
        for line in makefile.splitlines():
            if "$(INSTALL_" in line:
                self.assertTrue(line.startswith(chr(9)), "OpenWrt Makefile recipe requires tab")
        self.assertNotIn("uci commit", makefile)

    def test_manual_runner_contract(self):
        script = (CDN / "files/usr/libexec/cdn-optimizer/run-once").read_text()
        for expected in ("--manual-public-probe-authorized", "allow_public_probe", 'mkdir "$LOCK"', 'mv -f "$TMP" "$STATE/result.json"', 'rm -f "$STATE/result.json"'):
            self.assertIn(expected, script)
        self.assertNotIn("eval ", script)
        self.assertIn('[ "$(id -u)" = 0 ]', script)
        self.assertLess(script.index('mkdir "$LOCK"'), script.index('mkdir -m 0700 -p "$STATE"'))
        self.assertIn('wc -c < "$TMP"', script)
        self.assertIn('stat -c %u "$STATE"', script)
        self.assertIn('chmod 0700 "$STATE"', script)
        self.assertIn('[ ! -L "$STATE/result.json" ]', script)
        makefile = (CDN / "Makefile").read_text()
        self.assertIn("run-once", makefile)
        self.assertIn("rpcd/cdn-optimizer", makefile)
        rpcd = (CDN / "files/usr/libexec/rpcd/cdn-optimizer").read_text()
        self.assertNotIn("run-once", rpcd)

    def test_rpcd_process_contract_offline(self):
        plugin = str(CDN / "files/usr/libexec/rpcd/cdn-optimizer")
        listed = subprocess.run(["sh", plugin, "list"], input="{}", text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(listed.stdout), {"status": {}})
        for args in (["call", "scan"], ["call", "status", "extra"], ["delete"], []):
            rejected = subprocess.run(["sh", plugin, *args], input="{}", text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_manual_runner_fails_closed_without_consent(self):
        runner = str(CDN / "files/usr/libexec/cdn-optimizer/run-once")
        # Missing operator gate exits before mkdir, UCI, or any binary invocation.
        denied = subprocess.run(["sh", runner], text=True, capture_output=True)
        self.assertNotEqual(denied.returncode, 0)


if __name__ == "__main__":
    unittest.main()
