import importlib.util
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]/"openwrt"
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("pipeline",root/"dryrun_pipeline.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
SCAN={"schema_version":1,"safe_to_apply":False,"evidence":"latency_only",
      "candidates":[{"service":"github","ip":"151.101.1.133","pop":"TPE","latency_ms":5}]}

class PipelineTest(unittest.TestCase):
    def test_latency_never_authorizes_write(self):
        x=m.candidate_preview(SCAN,[{"domain":"raw.githubusercontent.com","answer":"151.101.2.133"}])
        self.assertTrue(x["dry_run"]);self.assertFalse(x["safe_to_apply"])
        self.assertEqual(x["candidate_count"],1)
    def test_invalid_schema_fail_closed(self):
        for data in ({**SCAN,"safe_to_apply":True},{**SCAN,"schema_version":2},{**SCAN,"candidates":None}):
            with self.assertRaises(ValueError):m.candidate_preview(data,[])
    def test_ignores_unrelated_existing_entries(self):
        x=m.candidate_preview(SCAN,[{"domain":"other.example","answer":"8.8.8.8"}])
        self.assertEqual(x["current_managed_domain_rewrites"],[])
if __name__=="__main__":unittest.main()
