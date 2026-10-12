#!/usr/bin/env python3
"""Read-only AdGuard Home DNS rewrite planner. No mutation endpoints are called.

Input JSON: {"records": [{"domain": "raw.githubusercontent.com", "answer": "203.0.113.1"}]}
Addresses are examples only; actual records must come from a verified scanner.
"""
import argparse
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.request

ALLOWED = frozenset({
    "release-assets.githubusercontent.com", "raw.githubusercontent.com",
    "pbs.twimg.com", "www.twitch.tv", "gql.twitch.tv",
    "static-cdn.jtvnw.net", "assets.twitch.tv", "k.twitchcdn.net",
})


def normalize(records):
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    result = {}
    for entry in records:
        if not isinstance(entry, dict) or set(entry) != {"domain", "answer"}:
            raise ValueError("records require exactly domain and answer")
        name = entry["domain"]
        if not isinstance(name, str) or name not in ALLOWED:
            raise ValueError("domain is not an explicitly allowed Fastly hostname")
        value = entry["answer"]
        if not isinstance(value, str):
            raise ValueError("answer must be an IPv4 string")
        ip = ipaddress.ip_address(value)
        if ip.version != 4 or not ip.is_global:
            raise ValueError("answer must be a public IPv4 address")
        if name in result:
            raise ValueError("duplicate hostname")
        result[name] = str(ip)
    if not result:
        raise ValueError("no records")
    return result


def plan(desired, existing):
    if not isinstance(existing, list):
        raise ValueError("AdGuard response must be an array")
    by_name = {}
    for r in existing:
        if not isinstance(r, dict):
            raise ValueError("invalid AdGuard rewrite entry")
        name = r.get("domain")
        if name in desired:
            if name in by_name:
                raise ValueError("duplicate existing rewrite; manual review required")
            by_name[name] = r.get("answer")
    actions = []
    for name, answer in sorted(desired.items()):
        old = by_name.get(name)
        if old is None:
            actions.append({"operation": "propose-add", "domain": name, "answer": answer})
        elif old == answer:
            actions.append({"operation": "unchanged", "domain": name, "answer": answer})
        else:
            # Never assume that existing rewrite belongs to us.
            actions.append({"operation": "conflict", "domain": name,
                            "existing": old, "proposed": answer})
    return actions


def read_rewrites(base_url, user, password):
    if not base_url.startswith("http://127.0.0.1:") and not base_url.startswith("http://localhost:"):
        raise ValueError("only local AdGuard HTTP API allowed")
    import base64
    token = base64.b64encode((user + ":" + password).encode()).decode()
    req = urllib.request.Request(base_url.rstrip("/") + "/control/rewrite/list",
                                 headers={"Authorization": "Basic " + token})
    with urllib.request.urlopen(req, timeout=8) as response:
        if response.status != 200:
            raise ValueError("AdGuard API did not return HTTP 200")
        return json.load(response)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, help="scanner-produced JSON file")
    parser.add_argument("--adguard-url", default="http://127.0.0.1:3000")
    args = parser.parse_args(argv)
    try:
        with open(args.candidates, encoding="utf-8") as f:
            desired = normalize(json.load(f).get("records"))
        user = os.environ.get("ADGUARD_USER")
        password = os.environ.get("ADGUARD_PASSWORD")
        if not user or not password:
            raise ValueError("ADGUARD_USER and ADGUARD_PASSWORD must be set")
        actions = plan(desired, read_rewrites(args.adguard_url, user, password))
        json.dump({"dry_run": True, "actions": actions}, sys.stdout, indent=2)
        print()
        return 2 if any(a["operation"] == "conflict" for a in actions) else 0
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print("Planner failed: " + str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
