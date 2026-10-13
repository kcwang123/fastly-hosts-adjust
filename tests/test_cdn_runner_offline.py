"""Offline shell runtime tests: fixture-rewrite only; never touches actual router paths or public network."""
import os
import pathlib
import subprocess
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "openwrt/cdn-optimizer/files/usr/libexec/cdn-optimizer/run-once"

class RunnerOfflineRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in {
            "uci": '#!/bin/sh\ncase "$*" in *enabled*|*allow_public_probe*) echo 1;; *service*) echo github;; *candidate_ip*) echo 8.8.8.8;; *max_bytes*) echo 4096;; esac\n',
            "fastly-public-health": '#!/bin/sh\ncase "$MOCK_PROBE" in fail) exit 1;; esac\nprintf \'%s\\n\' \'{"schema_version":1,"safe_to_apply":false,"network_executed":true}\'\n',
        }.items():
            path=self.bin/name
            path.write_text(body)
            path.chmod(0o755)
        source=SOURCE.read_text()
        source=source.replace("STATE=/tmp/cdn-optimizer", f"STATE={self.root}/state")
        source=source.replace("LOCK=/tmp/cdn-optimizer.lock", f"LOCK={self.root}/lock")
        source=source.replace("PATH=/usr/sbin:/usr/bin:/sbin:/bin", f"PATH={self.bin}:/usr/sbin:/usr/bin:/sbin:/bin")
        source=source.replace('[ "$(id -u)" = 0 ]', '[ "0" = 0 ]')  # fixture-only root gate
        source=source.replace('[ "$3" = 0 ] && [ "$4" = 0 ]', '[ "$3" = "$(id -u)" ] && [ "$4" = "$(id -g)" ]')  # fixture-only UID/GID
        source=source.replace("/usr/bin/fastly-public-health --service", f"{self.bin}/fastly-public-health --service")
        self.script=self.root/"runner"
        self.script.write_text(source)
    def run_script(self, probe="ok", args=None):
        env=os.environ.copy()
        env["MOCK_PROBE"]=probe
        return subprocess.run(["sh",str(self.script),*(["--manual-public-probe-authorized"] if args is None else args)],
                              env=env,text=True,capture_output=True,timeout=4)
    def test_script_has_no_stat_dependency(self):
        self.assertNotIn("stat -c", self.script.read_text())
        self.assertIn("ls -ldn", self.script.read_text())

    def test_success_then_failure_invalidates_stale_status(self):
        good=self.run_script()
        self.assertEqual(good.returncode,0,good.stderr)
        result=self.root/"state/result.json"
        self.assertTrue(result.exists())
        self.assertFalse((self.root/"lock").exists())
        bad=self.run_script("fail")
        self.assertNotEqual(bad.returncode,0)
        self.assertFalse(result.exists())
        self.assertFalse((self.root/"lock").exists())
    def test_lock_prevents_overlap_and_does_not_delete_lock(self):
        (self.root/"lock").mkdir()
        p=self.run_script()
        self.assertEqual(p.returncode,3)
        self.assertTrue((self.root/"lock").exists())
        self.assertFalse((self.root/"state/result.json").exists())
    def test_missing_gate_never_creates_state(self):
        p=self.run_script(args=[])
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.root/"state").exists())
    def test_state_symlink_denied(self):
        (self.root/"state").symlink_to(self.root/"bin",target_is_directory=True)
        p=self.run_script()
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.root/"lock").exists())

if __name__=="__main__":
    unittest.main()
