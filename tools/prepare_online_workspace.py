"""Stage owned Online source into a fresh ignored workspace; never run a game."""
from pathlib import Path
import argparse,json,shutil,sys
sys.dont_write_bytecode=True
from online_build_common import ROOT,SOURCE,DEFAULT_WORKSPACE,workspace_path,stage_runtime,sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--runtime-dir',type=Path,help='Optional full verified runtime, e.g. package/payload/online/runtime')
    group.add_argument('--runtime-archive',type=Path,help='Optional pinned official embeddable CPython archive')
    a=p.parse_args()
    try:workspace=workspace_path(a.workspace,require=False)
    except ValueError as error:p.error(str(error))
    if workspace.exists():p.error('Choose a fresh workspace; never replace existing builds or ledgers')
    workspace.mkdir(parents=True);mapping={}
    sources=[(SOURCE/'online_launcher.cpp','src/online_launcher.cpp'),(SOURCE/'broker.py','payload/online/broker.py'),
        (SOURCE/'workspace_build_launcher.py','build_launcher.py'),(SOURCE/'workspace_run_tests.py','run_tests.py')]
    sources += [(path,'tests/'+path.name) for path in sorted((SOURCE/'tests').glob('*')) if path.suffix in ('.py','.cpp')]
    sources += [(path,'payload/'+path.relative_to(SOURCE/'scripts').as_posix()) for path in sorted((SOURCE/'scripts').rglob('*')) if path.is_file()]
    for source,relative in sources:
        if source.is_symlink():p.error('Source symlinks are not allowed')
        target=workspace/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        mapping[relative]={'source':source.relative_to(ROOT).as_posix(),'sha256':sha(source.read_bytes())}
    marker={'format':'PET-SOCCER-ONLINE-SOURCE-WORKSPACE-1','version':'0.2.0-beta.1','source_files':mapping,
        'game_or_native_renderer_launched':False}
    (workspace/'WORKSPACE.json').write_bytes((json.dumps(marker,indent=2)+'\n').encode('utf8'))
    if a.runtime_dir or a.runtime_archive:
        try:stage_runtime(workspace,archive=a.runtime_archive,runtime_dir=a.runtime_dir)
        except ValueError as error:p.error(str(error))
    print('Prepared owned Online workspace:',workspace)

if __name__=='__main__':main()
