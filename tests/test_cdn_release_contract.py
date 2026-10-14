"""Disposable package metadata upgrade/rollback contract, NOT an opkg engine test."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.1.0-1"
NEW = "0.1.0-2"

def version_from_makefile(path):
    txt = path.read_text()
    def get(key):
        m = re.search(r"^" + key + r":=([^\s]+)$", txt, re.M)
        if m is None:
            raise ValueError("missing " + key)
        return m.group(1)
    return get("PKG_VERSION") + "-" + get("PKG_RELEASE")

def control(name, version, depends, arch):
    return {"Package": name, "Version": version, "Depends": depends, "Architecture": arch}

def transaction(db, incoming, *, expect_current):
    """In-memory disposable fixture; enforces precondition and models versioned replacement only."""
    updated = dict(db)
    package = incoming["Package"]
    if package not in db or db[package]["Version"] != expect_current:
        raise ValueError("unexpected installed version")
    updated[package] = dict(incoming)
    return updated

class ReleaseContract(unittest.TestCase):
    def test_both_packages_have_distinct_next_release(self):
        for name in ("cdn-optimizer", "luci-app-cdn-optimizer"):
            with self.subTest(name=name):
                self.assertEqual(version_from_makefile(ROOT / "openwrt" / name / "Makefile"), NEW)
                self.assertNotEqual(OLD, NEW)

    def test_disposable_upgrade_then_rollback(self):
        core_old = control("cdn-optimizer", OLD, "libc, ca-bundle", "aarch64_cortex-a53")
        core_new = control("cdn-optimizer", NEW, "libc, ca-bundle, jsonfilter", "aarch64_cortex-a53")
        luci_old = control("luci-app-cdn-optimizer", OLD, "libc, cdn-optimizer, luci-base", "all")
        luci_new = control("luci-app-cdn-optimizer", NEW, "libc, cdn-optimizer, luci-base", "all")
        original = {x["Package"]: x for x in (core_old, luci_old)}
        updated = transaction(original, core_new, expect_current=OLD)
        updated = transaction(updated, luci_new, expect_current=OLD)
        self.assertIn("jsonfilter", updated["cdn-optimizer"]["Depends"])
        self.assertEqual(original["cdn-optimizer"]["Depends"], "libc, ca-bundle")
        restored = transaction(updated, core_old, expect_current=NEW)
        restored = transaction(restored, luci_old, expect_current=NEW)
        self.assertEqual(restored, original)

    def test_fail_closed_wrong_old_version(self):
        old = control("cdn-optimizer", OLD, "libc, ca-bundle", "aarch64_cortex-a53")
        new = control("cdn-optimizer", NEW, "libc, ca-bundle, jsonfilter", "aarch64_cortex-a53")
        with self.assertRaisesRegex(ValueError, "unexpected installed version"):
            transaction({"cdn-optimizer": old}, new, expect_current=NEW)

    def test_source_does_not_automatically_apply_network(self):
        for name in ("cdn-optimizer", "luci-app-cdn-optimizer"):
            source = (ROOT / "openwrt" / name / "Makefile").read_text()
            self.assertNotIn("uci commit", source)
            self.assertNotIn("/etc/init.d/rpcd restart", source)
            self.assertNotIn("/etc/init.d/uhttpd restart", source)

if __name__ == "__main__":
    unittest.main()
