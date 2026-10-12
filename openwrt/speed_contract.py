"""Strict read-only route performance evidence contract.

This module validates evidence only. It never manufactures write authorization.
Individual hostname/SNI validation and real speed probes must precede this input.
"""
import ipaddress
import math
import statistics

def check_evidence(document, *, max_bytes, min_improvement_percent, minimum_rounds=3):
    if type(document) is not dict or document.get("schema_version") != 2:
        raise ValueError("unsupported speed evidence schema")
    if document.get("safe_to_apply") is not False:
        raise ValueError("evidence must remain read-only")
    used = document.get("bytes_downloaded")
    if type(used) is not int or not 0 <= used <= max_bytes:
        raise ValueError("scan exceeded byte budget")
    rows = document.get("measurements")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing route measurements")
    checked = []
    for item in rows:
        if not isinstance(item, dict) or set(item) != {"domain","ip","tls_verified",
                "sni_domain","baseline_mbps","candidate_mbps","http_status"}:
            raise ValueError("invalid measurement shape")
        domain = item["domain"]
        from tls_verify import SERVICES
        if domain not in SERVICES or item["sni_domain"] != domain or item["tls_verified"] is not True:
            raise ValueError("unverified hostname/TLS/SNI")
        addr = ipaddress.ip_address(item["ip"])
        if addr.version != 4 or not addr.is_global:
            raise ValueError("non-public address")
        if type(item["http_status"]) is not int or not 200 <= item["http_status"] < 400:
            raise ValueError("unhealthy HTTP probe")
        samples = []
        for k in ("baseline_mbps", "candidate_mbps"):
            values = item[k]
            if not isinstance(values, list) or len(values) < minimum_rounds or len(values) > 20:
                raise ValueError("insufficient bounded test rounds")
            if any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0 for v in values):
                raise ValueError("invalid bandwidth sample")
            samples.append(statistics.median(values))
        baseline, candidate = samples
        gain = 100 * (candidate / baseline - 1)
        checked.append({"domain":domain,"ip":str(addr),"median_baseline_mbps":baseline,
                        "median_candidate_mbps":candidate,"improvement_percent":round(gain,2),
                        "passes_threshold":gain >= min_improvement_percent})
    return {"read_only":True,"safe_to_apply":False,
            "measured_bytes":used,"results":checked}
