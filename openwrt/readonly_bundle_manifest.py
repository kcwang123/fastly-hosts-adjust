"""Explicit read-only OpenWrt deploy module manifest. No installation performed.

A bundle built from this allowlist cannot import AdGuard transaction writers.
It still must pass device preflight and requires independent egress approval.
"""
from pathlib import Path

READ_ONLY_MODULES = (
    "settings.py", "runner.py", "scanner_export.py", "tls_verify.py",
    "speed_contract.py", "benchmark_v3.py", "https_benchmark.py",
    "auto_targets.py", "egress_contract.py", "egress_reflector.py",
    "route_observer.py", "route_proposal.py", "readonly_launcher.py",
)
FORBIDDEN = frozenset(("rewrite_tx.py", "rewrite_recover.py",
                       "transaction_cli.py", "tx_safety.py"))
def validate(source):
    source = Path(source)
    if any(name in FORBIDDEN for name in READ_ONLY_MODULES):
        raise ValueError("write module in read-only deployment allowlist")
    for name in READ_ONLY_MODULES:
        p=source/name
        if p.is_symlink() or not p.is_file():
            raise ValueError("missing or symlink module: "+name)
        body=p.read_text(encoding="utf-8")
        for prohibited in ("from rewrite_tx import", "import rewrite_tx",
                           "from rewrite_recover import", "import rewrite_recover",
                           "from transaction_cli import", "import transaction_cli"):
            if prohibited in body:
                raise ValueError("read-only module references writer: "+name)
    return READ_ONLY_MODULES
