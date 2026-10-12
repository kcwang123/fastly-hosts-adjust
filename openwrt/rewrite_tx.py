"""Owned-only AdGuard Home rewrite transaction.

No network calls on import. The caller supplies an authenticated API object.
Never takes over an existing DNS rewrite, including identical entries.
A sidecar ownership registry is necessary because AdGuard rewrites have no owner tag.
"""
import ipaddress
import json
import os
import stat
from pathlib import Path

from adguard_plan import ALLOWED


def validate(desired):
    if not isinstance(desired, dict) or not desired:
        raise ValueError("desired must be a nonempty object")
    for domain, answer in desired.items():
        if domain not in ALLOWED or not isinstance(answer, str):
            raise ValueError("unsupported DNS rewrite")
        ip = ipaddress.ip_address(answer)
        if ip.version != 4 or not ip.is_global:
            raise ValueError("DNS rewrite must be a public IPv4")


def verify_private_file(path):
    path = Path(path)
    if not path.exists():
        return
    if path.is_symlink():
        raise ValueError("refuse symlink transaction state")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise ValueError("transaction state must be a private regular file")


def atomic_save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    verify_private_file(path)
    temp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    try:
        with open(temp, "x", encoding="utf-8") as f:
            json.dump(value, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def current_map(rows):
    if not isinstance(rows, list):
        raise ValueError("unexpected AdGuard response")
    values = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"domain", "answer"}:
            raise ValueError("unexpected AdGuard rewrite shape")
        key = row["domain"]
        if key in values:
            raise ValueError("duplicate AdGuard rewrite: " + key)
        values[key] = row["answer"]
    return values


def prepare(api, desired, ownership, snapshot_path):
    """Preflight and durable snapshot. No DNS writes."""
    validate(desired)
    if not isinstance(ownership, dict):
        raise ValueError("invalid ownership registry")
    before = current_map(api.list())
    for domain, desired_ip in desired.items():
        owned_ip = ownership.get(domain)
        actual_ip = before.get(domain)
        if owned_ip is None:
            if actual_ip is not None:
                raise ValueError("unowned rewrite conflict: " + domain)
        elif actual_ip != owned_ip:
            raise ValueError("owned rewrite has drifted: " + domain)
    snapshot = {"version": 1, "before": before,
                "ownership_before": dict(ownership), "desired": dict(desired),
                "phase": "prepared", "last_intent": None}
    if Path(snapshot_path).exists():
        raise ValueError("snapshot already exists; resolve prior transaction")
    atomic_save(snapshot_path, snapshot)
    return snapshot


def reconcile(api, desired, registry_path, snapshot_path, *, dry_run=True):
    """Apply only owned changes. On error undo changes whose live values still match our writes.

    Caller must hold an exclusive process lock. Registry and snapshot must live
    on persistent storage, not /tmp. Rollback conflicts cause an explicit error.
    """
    validate(desired)
    registry_path, snapshot_path = Path(registry_path), Path(snapshot_path)
    verify_private_file(registry_path)
    verify_private_file(snapshot_path)
    ownership = (json.loads(registry_path.read_text(encoding="utf-8"))
                 if registry_path.exists() else {})
    if not isinstance(ownership, dict):
        raise ValueError("invalid registry")
    before = current_map(api.list())
    operations = []
    for domain, target in sorted(desired.items()):
        actual = before.get(domain)
        owned = ownership.get(domain)
        if owned is None and actual is not None:
            raise ValueError("unowned rewrite conflict: " + domain)
        if owned is not None and actual != owned:
            raise ValueError("owned rewrite drift: " + domain)
        if actual != target:
            operations.append((domain, actual, target))
    if dry_run:
        return {"dry_run": True, "actions": [
            {"domain": d, "from": old, "to": target} for d, old, target in operations]}
    snapshot = prepare(api, desired, ownership, snapshot_path)
    try:
        updated = dict(ownership)
        for domain, old, target in operations:
            snapshot["phase"] = "applying"
            snapshot["last_intent"] = {"domain": domain, "old": old, "target": target}
            atomic_save(snapshot_path, snapshot)
            if old is not None:
                api.delete(domain, old)
            api.add(domain, target)
            updated[domain] = target
        live = current_map(api.list())
        if any(live.get(domain) != target for domain, target in desired.items()):
            raise RuntimeError("post-write verification failed")
        snapshot["phase"] = "committing"
        atomic_save(snapshot_path, snapshot)
        atomic_save(registry_path, updated)
        snapshot_path.unlink()
        return {"dry_run": False, "updated": len(operations)}
    except Exception as original:
        problems = []
        for domain, old, target in reversed(operations):
            try:
                live = current_map(api.list()).get(domain)
                if live == target:
                    api.delete(domain, target)
                elif live != old:
                    raise RuntimeError("concurrent modification: " + domain)
                if old is not None and current_map(api.list()).get(domain) is None:
                    api.add(domain, old)
                elif old is None and current_map(api.list()).get(domain) is not None:
                    raise RuntimeError("rollback conflict: " + domain)
            except Exception as e:
                problems.append(str(e))
        if not problems:
            snapshot_path.unlink()
        raise RuntimeError("transaction failed; " + ("rollback incomplete: " + "; ".join(problems)
                           if problems else "rollback completed")) from original
