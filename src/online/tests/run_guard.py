from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,time,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
if not (HERE.parent/'WORKSPACE.json').is_file():
    raise SystemExit('Use tools/prepare_online_workspace.py and tools/test_online.py; no test outputs belong in src.')
sys.path.insert(0,str(HERE.parent))
from build_launcher import compile_cpp
OUT=HERE/'guard-evidence';OUT.mkdir(exist_ok=True)
exe=OUT/'guard_test.exe'
compile_cpp(HERE/'launcher_guard_test.cpp',exe,console=True)
checks=[]

def run(*args):
    result=subprocess.run([str(exe),*map(str,args)],capture_output=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
    return result.returncode,result.stdout.decode().strip()

def check(name,condition):
    assert condition,name
    checks.append(name)

def wait_for_clear(root):
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        if run('--check',root)[0]==0:return
        time.sleep(.1)
    raise AssertionError('inert dummy did not exit')

with tempfile.TemporaryDirectory(prefix='inert-',dir=OUT) as tmp:
    a=Path(tmp)/'installA';b=Path(tmp)/'installB'
    for root in (a,b):
        root.mkdir()
        for name in ('PetSoccer.exe','PetSoccer.bum'):shutil.copyfile(exe,root/name)
    check('empty install is clear',run('--check',a)==(0,'CLEAR'))
    other=subprocess.Popen([str(b/'PetSoccer.bum'),'--worker','1600'],creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        check('same basename in other install does not block',run('--check',a)==(0,'CLEAR'))
        check('exact engine image detected',run('--check',b)==(10,'RUNNING'))
        check('case insensitive canonical path detected',run('--check',str(b).swapcase())==(10,'RUNNING'))
    finally:other.wait(timeout=4)
    bootstrap=subprocess.Popen([str(a/'PetSoccer.exe'),'--worker','1600'],creationflags=subprocess.CREATE_NO_WINDOW)
    try:check('exact short-lived bootstrap detected',run('--check',a)==(10,'RUNNING'))
    finally:bootstrap.wait(timeout=4)
    marker=Path(tmp)/'starts.txt'
    first=subprocess.Popen([str(exe),'--try',str(a),str(marker)],stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+2
    while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
    check('startup entered before engine exists',marker.exists())
    check('duplicate while bootstrap hands off is skipped',run('--try',a,marker)==(0,'SKIP'))
    check('first startup completes bounded handoff',first.communicate(timeout=5)[0].strip()==b'STARTED' and first.returncode==0)
    check('engine still detected after launcher exits',run('--check',a)==(10,'RUNNING'))
    check('duplicate after handoff is skipped',run('--try',a,marker)==(0,'SKIP'))
    check('only one bootstrap launched',marker.read_text().splitlines()==['START'])
    wait_for_clear(a)
    check('new launch allowed after prior engine exits',run('--try',a,marker)==(0,'STARTED'))
    wait_for_clear(a)
    # The executable files in private test installs may share disk storage.
    # Directory identity must still keep their independent startup locks apart.
    (b/'PetSoccer.exe').unlink();os.link(a/'PetSoccer.exe',b/'PetSoccer.exe')
    shared_a=Path(tmp)/'shared-a.txt';shared_b=Path(tmp)/'shared-b.txt'
    parallel=[subprocess.Popen([str(exe),'--try',str(root),str(mark)],stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW) for root,mark in ((a,shared_a),(b,shared_b))]
    outputs=[p.communicate(timeout=5)[0].strip() for p in parallel]
    check('separate installs with hardlinked bootstraps remain independent',outputs==[b'STARTED',b'STARTED'] and shared_a.exists() and shared_b.exists())
    wait_for_clear(a);wait_for_clear(b)
    race=Path(tmp)/'race.txt'
    contenders=[subprocess.Popen([str(exe),'--try',str(a),str(race)],stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(8)]
    outputs=[p.communicate(timeout=5)[0].strip() for p in contenders]
    check('eight concurrent clicks launch exactly one bootstrap',race.read_text().splitlines()==['START'] and outputs.count(b'STARTED')==1 and outputs.count(b'SKIP')==7)
    wait_for_clear(a)
    check('no permanent helper or game remains',run('--check',a)==(0,'CLEAR'))
report={'checks':checks,'passed':len(checks),'actual_game_launched':False,'broker_launched':False,
        'source_sha256':hashlib.sha256((HERE.parent/'src/online_launcher.cpp').read_bytes()).hexdigest()}
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
