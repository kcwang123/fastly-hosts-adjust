import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "openwrt" / "adguard_plan.py"
spec = importlib.util.spec_from_file_location("adguard_plan", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PlanTests(unittest.TestCase):
    def test_new_and_unchanged(self):
        desired = mod.normalize([{"domain": "raw.githubusercontent.com", "answer": "151.101.1.133"}])
        self.assertEqual(mod.plan(desired, [])[0]["operation"], "propose-add")
        self.assertEqual(mod.plan(desired, [{"domain": "raw.githubusercontent.com", "answer": "151.101.1.133"}])[0]["operation"], "unchanged")

    def test_existing_conflict_never_overwritten(self):
        desired = mod.normalize([{"domain": "raw.githubusercontent.com", "answer": "151.101.1.133"}])
        self.assertEqual(mod.plan(desired, [{"domain": "raw.githubusercontent.com", "answer": "151.101.2.133"}])[0]["operation"], "conflict")

    def test_reject_unknown_domain_and_private_ip(self):
        for name, address in [("example.com", "151.101.1.133"), ("raw.githubusercontent.com", "127.0.0.1")]:
            with self.assertRaises(ValueError):
                mod.normalize([{"domain": name, "answer": address}])

    def test_duplicate_candidates_rejected(self):
        with self.assertRaises(ValueError):
            mod.normalize([{"domain": "pbs.twimg.com", "answer": "151.101.1.159"},
                           {"domain": "pbs.twimg.com", "answer": "151.101.2.159"}])

    def test_duplicate_existing_rejected(self):
        with self.assertRaises(ValueError):
            mod.plan({"pbs.twimg.com": "151.101.1.159"},
                     [{"domain": "pbs.twimg.com", "answer": "151.101.1.159"},
                      {"domain": "pbs.twimg.com", "answer": "151.101.2.159"}])


if __name__ == "__main__":
    unittest.main()
