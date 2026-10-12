#!/usr/bin/env python3
"""Read-only scheduled Fastly scan runner. Never writes DNS or /etc/hosts."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from settings import Settings
from speed_contract import check_evidence
from dataclasses import replace


def read_state(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise ValueError("invalid state file")
    for key in ("last_health_epoch", "last_benchmark_epoch"):
        if key in value and (type(value[key]) is not int or value[key] < 0):
            raise ValueError("invalid state timestamp")
    return value


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".new." + str(os.getpid()))
    try:
        with temp.open("x", encoding="utf-8") as f:
            json.dump(value, f, sort_keys=True)
            f.write("\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def choose_mode(settings, state, now):
    due = settings.due(now, state.get("last_health_epoch"),
                       state.get("last_benchmark_epoch"))
    if due["benchmark"] and settings.auto_benchmark and state.get("last_health_epoch") is None:
        return "health"
    if due["benchmark"] and (settings.benchmark_targets or settings.auto_benchmark):
        return "benchmark"
    if due["health"]:
        return "health"
    if due["benchmark"]:
        return "benchmark_pending"
    return "skip"


def benchmark_due_with_config(settings, state, scan_path, now, config_path, executor=subprocess.run):
    """Run configured trusted targets; never mark success on partial failure."""
    if settings.auto_benchmark:
        from auto_targets import select
        from adguard_api import AdGuardAPI
        scan_file = Path(scan_path)
        age = time.time() - scan_file.stat().st_mtime
        if age < 0 or age > settings.max_scan_age_seconds:
            raise ValueError("scanner observation is stale")
        scan = json.loads(scan_file.read_text(encoding="utf-8"))
        credentials = (os.environ.get("ADGUARD_USER"), os.environ.get("ADGUARD_PASSWORD"))
        if not all(credentials):
            raise ValueError("AdGuard credentials required for auto benchmarking")
        api = AdGuardAPI("http://127.0.0.1:3000", *credentials, settings.api_timeout_seconds)
        targets = select(scan, settings.trusted_baselines, api.list())
        from egress_contract import read_and_validate
        read_and_validate(settings.egress_evidence_path, targets=targets,
                          max_age_seconds=settings.max_egress_age_seconds)
        # Even syntactically valid v1 JSON is self-asserted. It has no
        # cryptographic binding to independently observed target-specific paths.
        raise RuntimeError("automatic benchmarking blocked: trusted per-target egress attestation unavailable")

    outputs = []
    overall_deadline = time.monotonic() + settings.process_timeout_seconds
    count = len(settings.benchmark_targets)
    per_target = settings.max_benchmark_bytes // count if count else 0
    if per_target < 2 * settings.benchmark_rounds * settings.benchmark_sample_bytes:
        raise ValueError("global budget insufficient for all benchmark targets")
    for index, target in enumerate(settings.benchmark_targets):
        dest = Path(str(scan_path) + ".benchmark." + str(index) + ".json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        cmd = [sys.executable, str(Path(__file__).with_name("https_benchmark.py")),
               "--config", str(config_path),
               "--domain", target["domain"],
               "--baseline-ip", target["baseline_ip"],
               "--candidate-ip", target["candidate_ip"],
               "--output", str(dest), "--max-bytes", str(per_target)]
        # Run an isolated benchmark subprocess with an OS-enforced timeout.
        remaining = overall_deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd, settings.process_timeout_seconds)
        outcome = executor(cmd, timeout=remaining,
                           capture_output=True, text=True, check=False)
        if outcome.returncode != 0:
            raise RuntimeError("benchmark subprocess failed")
        bundle = json.loads(dest.read_text(encoding="utf-8"))
        from benchmark_v3 import verify
        verified = verify(bundle, settings, expected_target=target)
        outputs.append(verified)
    if sum(x["measured_bytes"] for x in outputs) > settings.max_benchmark_bytes:
        raise ValueError("aggregate benchmark exceeded configured limit")
    return {"benchmarks": outputs, "last_benchmark_epoch": now}


def run_once(settings, state_path, scan_path, now, executor=subprocess.run, config_path=None):
    state = read_state(state_path)
    mode = choose_mode(settings, state, now)
    if mode == "skip":
        return {"status": "skipped", "reason": "not_due"}
    if mode == "benchmark":
        if not config_path:
            return {"status": "error", "reason": "missing_benchmark_config_path"}
        try:
            result = benchmark_due_with_config(settings, state, scan_path, now, config_path, executor)
            state["last_benchmark_epoch"] = now
            atomic_json(state_path, state)
            return {"status": "ok", "mode": "benchmark", "targets": len(result["benchmarks"]),
                    "safe_to_apply": False}
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            return {"status": "error", "reason": type(exc).__name__}
    if mode == "benchmark_pending":
        # Fail safely instead of pretending a latency scan is a full benchmark.
        return {"status": "pending", "reason": "full_benchmark_not_implemented"}
    # Only a latency scan; no changes to any DNS setting.
    Path(scan_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(Path(__file__).with_name("scanner_export.py")),
           "--services", *settings.enabled_services,
           "--output", str(scan_path)]
    for attempt in range(settings.retry_count + 1):
        try:
            Path(scan_path).unlink(missing_ok=True)
            result = executor(cmd, timeout=settings.process_timeout_seconds,
                              capture_output=True, text=True, check=False)
            if result.returncode == 0:
                data = json.loads(Path(scan_path).read_text(encoding="utf-8"))
                if data.get("safe_to_apply") is not False or data.get("evidence") != "latency_only":
                    raise ValueError("unexpected scanner evidence contract")
                state["last_health_epoch"] = now
                atomic_json(state_path, state)
                return {"status": "ok", "mode": "health",
                        "candidates": len(data.get("candidates", []))}
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            error = type(exc).__name__
        else:
            error = "scanner_exit_" + str(result.returncode)
        if attempt < settings.retry_count:
            time.sleep(settings.retry_delay_seconds)
    return {"status": "error", "reason": error}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--state", default="/tmp/fastly-optimizer/state.json")
    parser.add_argument("--scan-output", default="/tmp/fastly-optimizer/scan.json")
    args = parser.parse_args(argv)
    settings = Settings.load(args.config)
    # flock available on OpenWrt BusyBox; use external lock wrapper before cron.
    outcome = run_once(settings, args.state, args.scan_output, int(time.time()), config_path=args.config)
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["status"] in ("ok", "skipped", "pending") else 1


if __name__ == "__main__":
    raise SystemExit(main())
