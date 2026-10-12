"""Run bundled read-only CLI with an explicitly restricted Python environment.

Not an OS sandbox. Must not be installed with elevated write permissions.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--state",required=True)
    parser.add_argument("--scan-output",required=True)
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parent
    # -I ignores PYTHONPATH, PYTHONHOME and user site packages, but it also
    # omits the script directory. Explicitly insert only this reviewed bundle.
    script="import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=['runner.py']+sys.argv[2:];runpy.run_path(sys.path[0]+'/runner.py',run_name='__main__')"
    env={"PATH":os.defpath,"LANG":"C","LC_ALL":"C","PYTHONDONTWRITEBYTECODE":"1"}
    completed=subprocess.run(
        [sys.executable,"-I","-B","-c",script,str(root),
         "--config",args.config,"--state",args.state,"--scan-output",args.scan_output],
        env=env,check=False)
    return completed.returncode

if __name__=="__main__":
    raise SystemExit(main())
