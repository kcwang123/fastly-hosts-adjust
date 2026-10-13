#!/usr/bin/env python3
"""Read-only bounded rpcd readiness verification; never restarts services."""
import argparse
import json
import subprocess
import time

EXPECTED_SHA = "721a034c1ebf275eceb88637b0626cf9527d7af38b469d37a669969d765f1081"

def validate(methods, status):
    if '"status":{}' not in methods or '"scan"' in methods:
        raise ValueError("unexpected method contract")
    data = json.loads(status)
    if data.get("schema_version") != 1 or data.get("status") != "not_tested" or data.get("safe_to_apply") is not False:
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
    if len(lines) != 3 or lines[0].split()[0] != EXPECTED_SHA or lines[1:] != ["0", "0"]:
        raise RuntimeError("READONLY_PREFLIGHT_FAILED")
    def probe():
        return ssh("ubus -v list cdn-optimizer"), ssh("ubus call cdn-optimizer status")
    attempt = poll(probe, args.attempts, args.interval)
    print(f"RPCD_READONLY_READY attempt={attempt}; methods=status_only; safe_to_apply=false; no restart/probe")

if __name__ == "__main__":
    main()
