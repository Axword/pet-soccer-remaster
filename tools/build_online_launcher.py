"""Build the owned x86 launcher inside an ignored workspace; no game launch."""
from pathlib import Path
import argparse,subprocess,sys
sys.dont_write_bytecode=True
from online_build_common import DEFAULT_WORKSPACE,workspace_path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    p.add_argument('--vcvars',type=Path,help='Optional external MSVC vcvars32.bat')
    a=p.parse_args()
    try:workspace=workspace_path(a.workspace)
    except (ValueError,FileNotFoundError) as error:p.error(str(error))
    command=[sys.executable,str(workspace/'build_launcher.py')]
    if a.vcvars:command += ['--vcvars',str(a.vcvars.resolve())]
    result=subprocess.run(command,cwd=workspace,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    sys.stdout.write((result.stdout+result.stderr).decode('utf8','replace'))
    if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':main()
