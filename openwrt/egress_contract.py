"""Read-only egress evidence contract. No router changes and no inference from a flag.

Evidence must be produced by an independent trusted operator/probe. Route dumps
alone cannot prove that two CDN connections share a public WARP/PBR exit.
"""
import ipaddress
import json
import time
from pathlib import Path

def validate_evidence(document, *, targets, max_age_seconds, now=None):
    now = time.time() if now is None else now
    if not isinstance(document, dict) or set(document) != {"version", "observed_epoch", "observations", "read_only"}:
        raise ValueError("invalid egress evidence schema")
    if document["version"] != 1 or document["read_only"] is not True:
        raise ValueError("untrusted egress evidence")
    ts=document["observed_epoch"]
    if type(ts) not in (int,float) or not 0 <= now-ts <= max_age_seconds:
        raise ValueError("egress evidence stale or future-dated")
    entries=document["observations"]
    if not isinstance(entries,list) or len(entries) != len(targets):
        raise ValueError("egress observation count mismatch")
    seen=set()
    for item in entries:
        required={"domain","baseline_ip","candidate_ip","baseline_egress_ip",
                  "candidate_egress_ip","baseline_interface","candidate_interface",
                  "baseline_route","candidate_route","method"}
        if not isinstance(item,dict) or set(item) != required:
            raise ValueError("incomplete egress observation")
        pair=(item["domain"],item["baseline_ip"],item["candidate_ip"])
        if pair in seen or pair not in {(t["domain"],t["baseline_ip"],t["candidate_ip"]) for t in targets}:
            raise ValueError("egress targets do not match")
        seen.add(pair)
        for k in ("baseline_egress_ip","candidate_egress_ip"):
            v=ipaddress.ip_address(item[k])
            if not v.is_global or v.version != 4:
                raise ValueError("egress must be global IPv4")
        if item["baseline_egress_ip"] != item["candidate_egress_ip"]:
            raise ValueError("different public egress")
        for k in ("baseline_interface","candidate_interface","baseline_route","candidate_route"):
            if not isinstance(item[k],str) or not item[k].strip() or len(item[k]) > 256:
                raise ValueError("missing route observation")
        if item["baseline_interface"] != item["candidate_interface"]:
            raise ValueError("different route interface")
        if item["method"] != "independent-https-probe-per-route":
            raise ValueError("route dump alone cannot prove public egress")
    return {"read_only":True,"egress_consistent":True,"observed_epoch":ts}

def read_and_validate(path, *, targets, max_age_seconds):
    path=Path(path)
    if path.is_symlink():
        raise ValueError("symlink egress evidence forbidden")
    return validate_evidence(json.loads(path.read_text(encoding="utf-8")),
                             targets=targets,max_age_seconds=max_age_seconds)
