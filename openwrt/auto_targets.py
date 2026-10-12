"""Candidate selection for automatic read-only benchmarks.

No system resolver is used as baseline. Baselines must be pinned in config,
and any AdGuard rewrite for a selected hostname blocks automatic comparison.
"""
import ipaddress
from route_proposal import SERVICE_DOMAIN, public_ipv4


def select(scan, trusted_baselines, existing_rewrites, *, max_targets=2):
    if (not isinstance(scan, dict) or scan.get("schema_version") != 1
            or scan.get("safe_to_apply") is not False
            or scan.get("evidence") != "latency_only"):
        raise ValueError("invalid scan evidence")
    if not isinstance(existing_rewrites, list) or not isinstance(trusted_baselines, dict):
        raise ValueError("missing trusted inputs")
    entries = scan.get("candidates")
    if not isinstance(entries, list):
        raise ValueError("missing candidates")
    if not 1 <= max_targets <= 8:
        raise ValueError("invalid max_targets")
    blocked = set()
    for row in existing_rewrites:
        if not isinstance(row, dict) or "domain" not in row:
            raise ValueError("malformed AdGuard rewrite inventory")
        blocked.add(row["domain"])
    output = []
    for service, domain in SERVICE_DOMAIN.items():
        if domain not in trusted_baselines:
            continue
        if domain in blocked:
            raise ValueError("AdGuard rewrite contaminates baseline for " + domain)
        baseline = trusted_baselines[domain]
        if not public_ipv4(baseline):
            raise ValueError("invalid pinned baseline")
        valid = sorted((r for r in entries if isinstance(r, dict)
                        and r.get("service") == service and public_ipv4(r.get("ip"))
                        and type(r.get("latency_ms")) in (int, float)
                        and 0 <= r["latency_ms"] <= 30000),
                       key=lambda r:r["latency_ms"])
        ip = next((r["ip"] for r in valid if r["ip"] != baseline), None)
        if ip:
            output.append({"domain":domain,"baseline_ip":baseline,"candidate_ip":ip})
        if len(output) == max_targets:
            break
    if not output:
        raise ValueError("no approved benchmark pair")
    return output
