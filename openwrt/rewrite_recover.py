"""Conservative recovery of interrupted AdGuard rewrite transaction.

Only modifies hostnames in saved desired set that were owned at snapshot time
or did not exist before the transaction. Never touches other rewrite entries.
Caller must hold the same exclusive lock as the transaction writer.
"""
import json
from pathlib import Path
from rewrite_tx import current_map, atomic_save, verify_private_file


def recover(api, registry_path, snapshot_path, *, dry_run=True):
    snapshot_path = Path(snapshot_path)
    verify_private_file(snapshot_path)
    verify_private_file(registry_path)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        raise ValueError("unsupported recovery snapshot")
    before = snapshot.get("before")
    ownership = snapshot.get("ownership_before")
    desired = snapshot.get("desired")
    if not isinstance(before, dict) or not isinstance(ownership, dict) or not isinstance(desired, dict):
        raise ValueError("invalid recovery snapshot")
    from rewrite_tx import validate
    validate(desired)
    for domain in desired:
        old = before.get(domain)
        if domain not in ownership and old is not None:
            raise ValueError("snapshot contains unowned DNS rewrite")
        if domain in ownership and ownership[domain] != old:
            raise ValueError("snapshot ownership mismatch")
    current = current_map(api.list())
    actions = []
    for domain, wanted in sorted(desired.items()):
        old = before.get(domain)
        live = current.get(domain)
        if live == old:
            continue
        if live not in (None, wanted):
            raise ValueError("unexpected concurrent DNS rewrite: " + domain)
        actions.append((domain, old, live))
    if dry_run:
        return {"dry_run": True, "actions": [{"domain": d, "restore": old, "current": live}
                                              for d, old, live in actions]}
    for domain, old, live in actions:
        if live is not None:
            api.delete(domain, live)
        if old is not None:
            api.add(domain, old)
        if current_map(api.list()).get(domain) != old:
            raise RuntimeError("recovery verification failed: " + domain)
    # Registry may have been committed just before crash. Restore original ownership.
    atomic_save(registry_path, ownership)
    snapshot_path.unlink()
    return {"dry_run": False, "restored": len(actions)}
