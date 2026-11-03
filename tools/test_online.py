"""Run portable console protocol/guard tests in a staged workspace; no renderer."""
from pathlib import Path
import argparse,json,subprocess,sys
sys.dont_write_bytecode=True
from online_build_common import DEFAULT_WORKSPACE,workspace_path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    p.add_argument('--suite',choices=('all','protocol','guard'),default='all')
    p.add_argument('--no-compile',action='store_true',help='Reuse an existing launcher probe in protocol tests')
    a=p.parse_args()
    try:workspace=workspace_path(a.workspace)
    except (ValueError,FileNotFoundError) as error:p.error(str(error))
    runtime=workspace/'payload/online/runtime/python.exe'
    if not runtime.is_file():p.error('First stage the pinned runtime with tools/build_online_runtime.py')
    suites=['protocol','guard'] if a.suite=='all' else [a.suite]
    for suite in suites:
        script=workspace/('run_tests.py' if suite=='protocol' else 'tests/run_guard.py')
        command=[str(runtime),'-I','-B',str(script)]
        if suite=='protocol' and a.no_compile:command += ['--no-compile']
        result=subprocess.run(command,cwd=workspace,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        sys.stdout.write((result.stdout+result.stderr).decode('utf8','replace'))
        if result.returncode:raise SystemExit(result.returncode)
    print(json.dumps({'suites':suites,'native_game_or_renderer_launched':False,'workspace':str(workspace)}))

if __name__=='__main__':main()
