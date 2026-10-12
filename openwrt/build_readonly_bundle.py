"""Reproducible source-only read-only bundle: no install, network, or router writes."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
from readonly_bundle_manifest import READ_ONLY_MODULES, FORBIDDEN, validate

DENIED = {Path(x).stem for x in FORBIDDEN} | {"adguard_api", "adguard_plan", "dryrun_pipeline"}
def imports(source):
    result=set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Import):
            result.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        fn=node.func
        dynamic=(isinstance(fn,ast.Name) and fn.id=="__import__") or (
            isinstance(fn,ast.Attribute) and fn.attr=="import_module")
        if dynamic and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
            result.add(node.args[0].value.split(".")[0])
    return result

def build(source, destination):
    source=Path(source); destination=Path(destination)
    names=validate(source)
    if destination.exists():
        raise ValueError("destination must not exist")
    local={p.stem for p in source.glob("*.py")}
    expected=set(names)
    if any(imports((source/name).read_text(encoding="utf-8")) & DENIED for name in names):
        raise ValueError("write-capable module reachable")
    for name in names:
        unresolved=(imports((source/name).read_text(encoding="utf-8")) & local) - {Path(x).stem for x in expected}
        if unresolved:
            raise ValueError("unbundled local dependency: "+str(sorted(unresolved)))
    destination.mkdir(parents=True,mode=0o700)
    digests={}
    try:
        for name in sorted(names):
            data=(source/name).read_bytes()
            (destination/name).write_bytes(data)
            digests[name]=hashlib.sha256(data).hexdigest()
        metadata={"format":1,"files":digests,"read_only":True,"dns_writer_included":False}
        (destination/"manifest.json").write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
        verify(destination)
        return metadata
    except Exception:
        shutil.rmtree(destination)
        raise

def verify(destination):
    destination=Path(destination)
    manifest=json.loads((destination/"manifest.json").read_text())
    if manifest.get("format")!=1 or manifest.get("read_only") is not True or manifest.get("dns_writer_included") is not False:
        raise ValueError("invalid deployment manifest")
    expected=set(READ_ONLY_MODULES)
    if set(manifest.get("files",{}))!=expected or {p.name for p in destination.iterdir()}!=expected|{"manifest.json"}:
        raise ValueError("unexpected packaged files")
    local={Path(x).stem for x in expected}
    for name in expected:
        file=destination/name
        if file.is_symlink() or not file.is_file():
            raise ValueError("missing or symlink runtime module")
        if hashlib.sha256(file.read_bytes()).hexdigest()!=manifest["files"][name]:
            raise ValueError("modified module")
        deps=imports(file.read_text(encoding="utf-8"))
        if deps & DENIED:
            raise ValueError("forbidden dependency")
    return True

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default=str(Path(__file__).resolve().parent))
    parser.add_argument("--output",required=True)
    args=parser.parse_args(argv)
    build(args.source,args.output)
    return 0
if __name__=="__main__":sys.exit(main())
