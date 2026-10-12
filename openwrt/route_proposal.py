"""Fail-closed selection of benchmark IP pairs from latency observations.

A local baseline is resolved by the normal resolver; it is *not* presumed to
have the same CDN egress as a WARP/PBR route. These are benchmark proposals only.
"""
import ipaddress
import socket
from tls_verify import SERVICES

SERVICE_DOMAIN = {"github": "raw.githubusercontent.com",
                  "twitch": "static-cdn.jtvnw.net"}


def public_ipv4(value):
    try:
        ip = ipaddress.ip_address(value)
        return ip.version == 4 and ip.is_global
    except ValueError:
        return False


def resolve_baseline(domain, resolver=socket.getaddrinfo):
    if domain not in SERVICES:
        raise ValueError("unapproved benchmark domain")
    addresses = resolver(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
    candidates = sorted({item[4][0] for item in addresses if public_ipv4(item[4][0])})
    if not candidates:
        raise ValueError("no public baseline returned by resolver")
    return candidates[0]


def propose(scan, baseline_resolver=resolve_baseline, *, max_targets=2):
    if (not isinstance(scan, dict) or scan.get("schema_version") != 1
            or scan.get("evidence") != "latency_only"
            or scan.get("safe_to_apply") is not False):
        raise ValueError("untrusted scanner observation")
    rows = scan.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("missing candidates")
    if type(max_targets) is not int or not 1 <= max_targets <= 8:
        raise ValueError("invalid target limit")
    selected = []
    for service, domain in SERVICE_DOMAIN.items():
        choices = [r for r in rows if isinstance(r, dict) and r.get("service") == service
                   and public_ipv4(r.get("ip")) and type(r.get("latency_ms")) in (int, float)
                   and 0 <= r["latency_ms"] <= 30000]
        if not choices:
            continue
        baseline = baseline_resolver(domain)
        if not public_ipv4(baseline):
            raise ValueError("invalid resolver baseline")
        candidates = sorted(choices, key=lambda r: r["latency_ms"])
        best = next((r["ip"] for r in candidates if r["ip"] != baseline), None)
        if best is not None:
            selected.append({"domain": domain, "baseline_ip": baseline,
                             "candidate_ip": best, "source": "latency_proposal"})
        if len(selected) >= max_targets:
            break
    if not selected:
        raise ValueError("no distinct benchmark pair")
    return {"safe_to_apply": False, "targets": selected,
            "warning": "baseline may use a different PBR/WARP egress; validate on router"}
