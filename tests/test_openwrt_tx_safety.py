import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("tx_safety",root/"tx_safety.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class SafetyTest(unittest.TestCase):
    def test_directory_permissions(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t)/"state";d.mkdir(mode=0o700)
            m.verify_state_paths(d/"registry.json",d/"snapshot.json")
            d.chmod(0o755)
            with self.assertRaises(ValueError):m.verify_state_paths(d/"registry.json",d/"snapshot.json")
    def test_private_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t)/"state";d.mkdir(mode=0o700)
            (d/"registry.json").write_text("{}")
            with self.assertRaises(ValueError):m.verify_state_paths(d/"registry.json",d/"snapshot.json")
            (d/"registry.json").chmod(0o600)
            m.verify_state_paths(d/"registry.json",d/"snapshot.json")
            (d/"snapshot.json").symlink_to(d/"registry.json")
            with self.assertRaises(ValueError):m.verify_state_paths(d/"registry.json",d/"snapshot.json")
    def test_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as t:
            lock=Path(t)/"lock"
            with m.ExclusiveLock(lock):
                with self.assertRaises(RuntimeError):
                    with m.ExclusiveLock(lock): pass
            self.assertFalse(lock.exists())
if __name__=="__main__":unittest.main()
