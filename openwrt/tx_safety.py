"""Persistent transaction safety helpers. Fail closed on unsafe paths or stale locks."""
import os
from pathlib import Path
import stat
from rewrite_tx import atomic_save, verify_private_file

def verify_state_directory(path):
    directory = Path(path)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("transaction directory must exist and not be symlink")
    info = directory.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("transaction directory must be owned by process and mode 0700")
    return directory

def verify_state_paths(registry, snapshot):
    registry, snapshot = Path(registry), Path(snapshot)
    if registry == snapshot or registry.parent != snapshot.parent:
        raise ValueError("registry and snapshot must be distinct siblings")
    verify_state_directory(registry.parent)
    verify_private_file(registry)
    verify_private_file(snapshot)

class ExclusiveLock:
    """Use exclusive mkdir; stale locks need explicit manual intervention."""
    def __init__(self, path):
        self.path = Path(path)
        self.owned = False
    def __enter__(self):
        if self.path.is_symlink():
            raise RuntimeError("symlink lock rejected")
        try:
            self.path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise RuntimeError("transaction lock already exists") from exc
        self.owned = True
        return self
    def __exit__(self, *exc):
        if self.owned:
            self.path.rmdir()
            self.owned = False
