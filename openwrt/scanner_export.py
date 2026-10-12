#!/usr/bin/env python3
"""Export upstream Fastly scan observations as JSON, without modifying DNS/hosts.

Latency-only observations are NOT approved for automatic DNS rewrites.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import sys

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "fastly_hosts.py"


def load_upstream():
    spec = importlib.util.spec_from_file_location("fastly_hosts", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_scan(upstream, services, max_candidates):
    keys = upstream.scan_keys([s for s in upstream.BUILTIN if s["key"] in services])
    if not keys:
        raise ValueError("no scannable services")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        raw = upstream.scan("OpenWrt scan", keys, near_only=True)
    records = []
    for key in keys:
        for candidate in raw["found"].get(key, [])[:max_candidates]:
            records.append({"service": key, "ip": candidate["ip"], "pop": candidate["pop"],
                            "latency_ms": round(candidate["latency_ms"], 2)})
    return {"schema_version": 1, "source": "fastly-hosts-adjust",
            "evidence": "latency_only", "safe_to_apply": False,
            "scanned_blocks": raw["scanned"], "skipped_blocks": raw["skipped"],
            "candidates": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--services", nargs="+", choices=["github", "x", "twitch"],
                        default=["github", "twitch"])
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    if not 1 <= args.max_candidates <= 20:
        parser.error("max-candidates must be between 1 and 20")
    upstream = load_upstream()
    data = run_scan(upstream, args.services, args.max_candidates)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)
    return 0 if data["candidates"] else 1


if __name__ == "__main__":
    sys.exit(main())
