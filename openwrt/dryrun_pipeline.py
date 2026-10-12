"""Read-only integration of scanner evidence and AdGuard rewrite inventory.

Deliberately refuses to promote latency-only evidence to a write authorization.
"""
import argparse
import json
from pathlib import Path
from adguard_api import AdGuardAPI
from adguard_plan import ALLOWED, plan, normalize
from settings import Settings
from speed_contract import check_evidence


def candidate_preview(scan, existing, settings=None):
    if isinstance(scan, dict) and scan.get("schema_version") == 2:
        if settings is None:
            raise ValueError("speed evidence requires validated settings")
        evidence = check_evidence(scan, max_bytes=settings.max_benchmark_bytes,
                                  min_improvement_percent=settings.min_improvement_percent)
        return {"dry_run": True, "safe_to_apply": False,
                "evidence": "speed_validated_preview", "speed": evidence,
                "current_managed_domain_rewrites": [
                    {"domain": r["domain"], "answer": r["answer"]} for r in existing
                    if isinstance(r, dict) and r.get("domain") in ALLOWED]}

    if not isinstance(scan, dict) or scan.get("schema_version") != 1:
        raise ValueError("unsupported scanner contract")
    if scan.get("safe_to_apply") is not False or scan.get("evidence") != "latency_only":
        raise ValueError("unexpected scanner safety contract")
    rows = scan.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("missing scan candidates")
    # Candidate observations are *not* the verified hostname-IP records
    # required for a write. Do not infer an address for unrelated hostnames.
    candidates = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("ip"), str):
            raise ValueError("invalid candidate")
        if row.get("service") not in ("github", "twitch"):
            raise ValueError("unsupported candidate service")
        candidates.append({"service": row["service"], "ip": row["ip"],
                           "pop": row.get("pop"), "latency_ms": row.get("latency_ms")})
    if not isinstance(existing, list):
        raise ValueError("invalid rewrite inventory")
    return {"dry_run": True, "safe_to_apply": False,
            "evidence": "latency_only", "candidate_count": len(candidates),
            "candidates": candidates,
            "current_managed_domain_rewrites": [
                {"domain": r["domain"], "answer": r["answer"]}
                for r in existing if isinstance(r, dict) and r.get("domain") in ALLOWED]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--scan-json", required=True)
    p.add_argument("--adguard-url", default="http://127.0.0.1:3000")
    args = p.parse_args(argv)
    cfg = Settings.load(args.config)
    if not cfg.dry_run:
        raise ValueError("pipeline requires dry_run=true")
    import os
    user, password = os.environ.get("ADGUARD_USER"), os.environ.get("ADGUARD_PASSWORD")
    if not user or not password:
        raise ValueError("AdGuard credentials missing")
    scan = json.loads(Path(args.scan_json).read_text(encoding="utf-8"))
    api = AdGuardAPI(args.adguard_url, user, password, cfg.api_timeout_seconds)
    print(json.dumps(candidate_preview(scan, api.list(), cfg), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
