"""Document first-run scheduler priority without network calls."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"openwrt"))
from runner import choose_mode
from settings import Settings
class DueBoundaryTests(unittest.TestCase):
 def test_default_first_run_health_without_benchmark_targets(self):
  self.assertEqual(choose_mode(Settings(),{},100000),"health")
 def test_explicit_diagnostic_targets_first_run(self):
  target={"domain":"raw.githubusercontent.com","baseline_ip":"151.101.2.133","candidate_ip":"151.101.1.133"}
  self.assertEqual(choose_mode(Settings(benchmark_targets=(target,)),{},100000),"benchmark")
 def test_auto_mode_requires_health_first(self):
  self.assertEqual(choose_mode(Settings(auto_benchmark=True),{},100000),"health")
 def test_health_becomes_due_even_if_benchmark_completed(self):
  settings=Settings()
  self.assertEqual(choose_mode(settings,{"last_benchmark_epoch":100000},100000+3600),"health")
 def test_benchmark_with_no_targets_is_pending_after_health_fresh(self):
  settings=Settings()
  self.assertEqual(choose_mode(settings,{"last_health_epoch":100000},100000+1),"benchmark_pending")
 def test_neither_due(self):
  settings=Settings()
  self.assertEqual(choose_mode(settings,{"last_health_epoch":100000,"last_benchmark_epoch":100000},100001),"skip")
if __name__=="__main__":unittest.main()
