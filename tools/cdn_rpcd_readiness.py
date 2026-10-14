#!/usr/bin/env python3
"""Read-only bounded rpcd readiness verification; never restarts services."""
import argparse
import json
import re
import subprocess
import time

EXPECTED_SHA = "721a034c1ebf275eceb88637b0626cf9527d7af38b469d37a669969d765f1081"

def validate(methods, status):
    # ubus -v output is not JSON. Match exactly one method, with no additional
    # method names. Reject malformed output rather than substring matching.
    lines = [line.strip() for line in methods.splitlines() if line.strip()]
    if len(lines) != 2 or not re.fullmatch(r"'cdn-optimizer' @[0-9a-fA-F]+", lines[0]) or lines[1] != '"status":{}':
        raise ValueError("unexpected method contract")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate status field")
            result[key] = value
        return result
    data = json.loads(status, object_pairs_hook=unique_pairs)
    if not isinstance(data, dict) or set(data) != {"schema_version", "status", "safe_to_apply"}:
        raise ValueError("unexpected status fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["status"] != "not_tested" or data["safe_to_apply"] is not False:
        raise ValueError("unsafe or unexpected status")
    return True

def poll(probe, attempts=12, interval=2, sleep=time.sleep):
    if attempts < 1 or attempts > 30 or interval < 0 or interval > 10:
        raise ValueError("unbounded polling parameters")
    errors = []
    for idx in range(attempts):
        try:
            methods, status = probe()
            validate(methods, status)
            return idx + 1
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            errors.append(str(exc)[:160])
            if idx + 1 < attempts:
                sleep(interval)
    raise RuntimeError(f"READINESS_TIMEOUT attempts={attempts}; last={errors[-1]}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="kchomemainap")
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.host != "kchomemainap":
        parser.error("Only preapproved SSH alias kchomemainap supported")
    def ssh(cmd):
        p = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
             "-o", "ConnectTimeout=5", args.host, cmd],
            capture_output=True, text=True, timeout=12, check=True)
        return p.stdout
    # Gate hash and safety flags before polling; neither starts the public probe.
    preflight = ssh("sha256sum /usr/libexec/rpcd/cdn-optimizer; uci -q get cdn_optimizer.main.enabled; uci -q get cdn_optimizer.main.allow_public_probe")
    lines = [line.strip() for line in preflight.splitlines()]
    if len(lines) != 3 or lines[0] != EXPECTED_SHA + "  /usr/libexec/rpcd/cdn-optimizer" or lines[1:] != ["0", "0"]:
        raise RuntimeError("READONLY_PREFLIGHT_FAILED")
    def probe():
        return ssh("ubus -v list cdn-optimizer"), ssh("ubus call cdn-optimizer status")
    attempt = poll(probe, args.attempts, args.interval)
    print(f"RPCD_READONLY_READY attempt={attempt}; methods=status_only; safe_to_apply=false; no restart/probe")

if __name__ == "__main__":
    main()
