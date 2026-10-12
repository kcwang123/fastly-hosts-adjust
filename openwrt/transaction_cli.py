"""Single guarded entrypoint for DNS rewrite transaction and recovery.

The operator must pass explicit --apply or --recover; default is read-only.
No scheduler imports or calls this module.
"""
import argparse
import json
import os
from pathlib import Path

from adguard_api import AdGuardAPI
from rewrite_tx import reconcile
from rewrite_recover import recover
from settings import Settings
from tx_safety import ExclusiveLock, verify_state_paths


def execute(config, api, *, desired=None, mode="preview", lock_path=None):
    if mode not in ("preview", "apply", "recover-preview", "recover"):
        raise ValueError("unsupported operation")
    registry = Path(config.ownership_registry_path)
    snapshot = Path(config.transaction_snapshot_path)
    lock = Path(lock_path) if lock_path else registry.parent / "transaction.lock"
    verify_state_paths(registry, snapshot)
    if lock.parent != registry.parent or lock.is_symlink():
        raise ValueError("lock must be a sibling of persistent state files")
    if mode in ("apply", "recover"):
        raise ValueError("DNS rewrite write/recovery disabled: AdGuard API lacks atomic CAS")
    with ExclusiveLock(lock):
        if mode in ("recover", "recover-preview"):
            if not snapshot.exists():
                return {"status": "no_pending_transaction", "dry_run": mode != "recover"}
            return recover(api, registry, snapshot, dry_run=mode != "recover")
        if snapshot.exists():
            raise ValueError("pending transaction requires recovery before another update")
        if not isinstance(desired, dict):
            raise ValueError("desired rewrites required")
        return reconcile(api, desired, registry, snapshot, dry_run=mode != "apply")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--desired", help="JSON file of already independently validated rewrites")
    p.add_argument("--adguard-url", default="http://127.0.0.1:3000")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--recover", action="store_true")
    group.add_argument("--recover-preview", action="store_true")
    args = p.parse_args(argv)
    mode = ("apply" if args.apply else "recover" if args.recover
            else "recover-preview" if args.recover_preview else "preview")
    if mode in ("preview", "apply") and not args.desired:
        p.error("--desired required for preview/apply")
    cfg = Settings.load(args.config)
    user, password = os.environ.get("ADGUARD_USER"), os.environ.get("ADGUARD_PASSWORD")
    if not user or not password:
        raise ValueError("AdGuard credentials missing")
    api = AdGuardAPI(args.adguard_url, user, password, cfg.api_timeout_seconds)
    desired = json.loads(Path(args.desired).read_text(encoding="utf-8")) if args.desired else None
    print(json.dumps(execute(cfg, api, desired=desired, mode=mode), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
