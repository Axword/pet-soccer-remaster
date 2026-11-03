"""Verify and stage official CPython bytes into an existing isolated workspace."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
from online_build_common import DEFAULT_WORKSPACE,workspace_path,stage_runtime

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--archive',type=Path,help='Official CPython3.14.10 win32 embedded ZIP; SHA256 is pinned')
    group.add_argument('--runtime-dir',type=Path,help='Already extracted full runtime, including LICENSE.txt')
    a=p.parse_args()
    try:report=stage_runtime(workspace_path(a.workspace),a.archive,a.runtime_dir)
    except (ValueError,FileNotFoundError) as error:p.error(str(error))
    print(json.dumps(report))

if __name__=='__main__':main()
