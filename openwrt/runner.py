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
    if due["health"]:
        return "health"
    # Benchmark path is intentionally not supported until HTTPS/speed validation exists.
    if due["benchmark"]:
        return "benchmark_pending"
    return "skip"


def run_once(settings, state_path, scan_path, now, executor=subprocess.run):
    state = read_state(state_path)
    mode = choose_mode(settings, state, now)
    if mode == "skip":
        return {"status": "skipped", "reason": "not_due"}
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
    outcome = run_once(settings, args.state, args.scan_output, int(time.time()))
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["status"] in ("ok", "skipped", "pending") else 1


if __name__ == "__main__":
    raise SystemExit(main())
