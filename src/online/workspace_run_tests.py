"""Portable-runtime console tests only; never invoke launcher GUI or the game."""
from pathlib import Path
import argparse,hashlib,json,os,sqlite3,subprocess,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'payload/online'));sys.path.insert(0,str(HERE/'tests'))
def main():
    if not (HERE/"WORKSPACE.json").is_file():
        raise SystemExit("Use tools/prepare_online_workspace.py and tools/test_online.py; do not write tests into src.")
    parser=argparse.ArgumentParser();parser.add_argument('--no-compile',action='store_true');args=parser.parse_args()
    import asyncio,broker,test_launcher
    temporary_root=HERE/'tests/temporary';temporary_root.mkdir(parents=True,exist_ok=True)
    assert temporary_root.resolve().is_relative_to(HERE.resolve())
    tempfile.tempdir=str(temporary_root)
    # This process must itself be the shipped embedded interpreter for acceptance.
    runtime=HERE/'payload/online/runtime/python.exe'
    assert Path(sys.executable).resolve()==runtime.resolve(),'Run using payload/online/runtime/python.exe'
    with tempfile.TemporaryDirectory(prefix='portable-runtime-') as tmp:
        db=sqlite3.connect(str(Path(tmp)/'sqlite-smoke.sqlite3'));db.execute('CREATE TABLE smoke(v INTEGER)');db.execute('INSERT INTO smoke VALUES(58)');assert db.execute('SELECT v FROM smoke').fetchone()==(58,);db.close()
    if not args.no_compile:test_launcher.compile_probe()
    suite=unittest.defaultTestLoader.discover(str(HERE/'tests'),pattern='test_*.py')
    with (HERE/'test-results.log').open('w',encoding='utf8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report={'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
      'runtime':sys.version,'runtime_executable':str(sys.executable),'sqlite_version':sqlite3.sqlite_version,'broker_capabilities':7,
      'game_renderer_launched':False,'production_ports_or_databases_used':False}
    (HERE/'test-results.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report));return not result.wasSuccessful()
if __name__=='__main__':raise SystemExit(main())
