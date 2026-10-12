"""Read-only OpenWrt route observation. Never claims public egress attestation.

Uses ip -4 route get for each pinned destination; results are untrusted
diagnostics, NOT egress_contract v1 approval. No network connections made.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import time
from pathlib import Path

def observe(targets, *, runner=subprocess.run, now=None, timeout=3):
    observations = []
    if not isinstance(targets, list) or not targets:
        raise ValueError("targets required")
    for target in targets:
        if not isinstance(target, dict) or set(target) != {"domain", "baseline_ip", "candidate_ip"}:
            raise ValueError("invalid target")
        routes = {}
        for label in ("baseline", "candidate"):
            ip = target[label + "_ip"]
            import ipaddress
            addr = ipaddress.ip_address(ip)
            if addr.version != 4 or not addr.is_global:
                raise ValueError("non-global route destination")
            proc = runner(["ip", "-4", "route", "get", ip], capture_output=True,
                          text=True, timeout=timeout, check=False)
            if proc.returncode != 0:
                raise ValueError("route lookup failed")
            output = proc.stdout.strip()
            if not output or len(output) > 2048 or not re.search(r"\bdev\s+\S+", output):
                raise ValueError("incomplete route lookup")
            routes[label] = {"route": output, "interface": re.search(r"\bdev\s+(\S+)",output).group(1)}
        observations.append({**target, "baseline": routes["baseline"], "candidate": routes["candidate"]})
    payload={"version":1,"observed_epoch":time.time() if now is None else now,
             "method":"local-ip-route-get","read_only":True,"public_egress_verified":False,
             "observations":observations}
    return payload


def seal(payload, secret):
    """Tamper-evident local integrity, NOT route authenticity or public egress proof."""
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("key must be >=32 bytes")
    raw=json.dumps(payload, sort_keys=True, separators=(",",":")).encode()
    return {"payload":payload,"hmac_sha256":hmac.new(secret,raw,hashlib.sha256).hexdigest()}


def verify_seal(envelope, secret):
    if not isinstance(envelope, dict) or set(envelope) != {"payload","hmac_sha256"}:
        raise ValueError("invalid envelope")
    expected=seal(envelope["payload"],secret)["hmac_sha256"]
    if not hmac.compare_digest(expected,envelope["hmac_sha256"]):
        raise ValueError("egress observations failed integrity check")
    return envelope["payload"]


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--targets", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--timeout", type=float, default=3)
    args=p.parse_args(argv)
    targets=json.loads(Path(args.targets).read_text(encoding="utf-8"))
    result=observe(targets,timeout=args.timeout)
    # Deliberately output diagnostic-only document; cannot be accepted by egress_contract.
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
