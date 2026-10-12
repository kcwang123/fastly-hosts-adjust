"""Lock down supported scheduler entrypoint; no Router execution."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from readonly_bundle_manifest import READ_ONLY_MODULES
class Entrypoint(unittest.TestCase):
 def test_scheduler_only_calls_launcher(self):
  script=(Path(__file__).resolve().parents[1]/"openwrt"/"run.sh").read_text()
  self.assertIn("/readonly_launcher.py",script)
  self.assertNotIn("/runner.py",script)
  self.assertIn("readonly_launcher.py",READ_ONLY_MODULES)
 def test_no_writer_or_adguard_client_in_allowlist(self):
  self.assertFalse({"rewrite_tx.py","rewrite_recover.py","transaction_cli.py",
      "tx_safety.py","adguard_api.py"}&set(READ_ONLY_MODULES))
if __name__=="__main__":unittest.main()
