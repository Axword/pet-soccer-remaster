"""Build owned Online hooks from the pinned GMWL stage into a fresh local archive.

This never edits a game installation and never downloads/distributes stock code.
The paired options native bridge and CRLF menu overlay are also required.
"""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.patches import animal_identity,jagniellonia,team_visibility,online_ui,online_match

BASE_SHA='6fbcaedbdba9dacbda3e5921c4af16d8a928f3e9109108a71f0916ff17924cd4'
FAMILIES=('CXOnlineTransport','CXOnlineMenu','CXOnlineLobbyModel','CXOnlinePause',
    'CXOnlineVisibility','CXOnlineMatch','CXOnlineState','CXTeamVisibility',
    'CXAnimalIdentity','CXJagniellonia','CXOptions')

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',type=Path,required=True,help='Read-only original installation with its Java runtime')
    p.add_argument('--baseline',type=Path,required=True,help='Locally reconstructed GMWL stage containing code.pak and code_inf.pak')
    p.add_argument('--ecj',type=Path,required=True,help='External ECJ3.7.2 compiler supporting target1.3')
    p.add_argument('--output',type=Path,required=True,help='New isolated directory')
    a=p.parse_args();a.game=a.game.resolve();a.baseline=a.baseline.resolve();a.output=a.output.resolve()
    if a.output.exists() or a.output.is_relative_to(a.game) or a.output.is_relative_to(a.baseline):
        p.error('Output must be new and outside both input directories')
    baseline=a.baseline/'code.pak';index_file=a.baseline/'code_inf.pak'
    if sha(baseline.read_bytes())!=BASE_SHA:p.error('Unknown GMWL baseline; do not bypass the recipe fingerprints')
    java=a.game/'jre/bin/java.exe';boot=a.game/'jre/lib/rt.jar'
    for path in (java,boot,a.ecj,index_file):
        if not path.is_file():p.error('Missing external input: '+str(path))
    a.output.mkdir(parents=True);classes=a.output/'classes';classes.mkdir()
    sources=[ROOT/'src/java'/(name+'.java') for name in FAMILIES]
    command=[str(java),'-Xint','-cp',str(a.ecj.resolve()),'org.eclipse.jdt.internal.compiler.batch.Main',
        '-proc:none','-warn:none','-encoding','UTF-8','-source','1.3','-target','1.3',
        '-bootclasspath',str(boot),'-classpath',str(baseline),'-d',str(classes),*map(str,sources)]
    result=subprocess.run(command,capture_output=True,cwd=a.output,timeout=120)
    (a.output/'compile.stdout.txt').write_bytes(result.stdout);(a.output/'compile.stderr.txt').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('cp1250','replace'))
    with zipfile.ZipFile(baseline) as archive:
        infos=archive.infolist();before={row.filename:archive.read(row) for row in infos}
    merged=dict(before);recipes=[]
    for name,recipe in [('animal_identity',animal_identity.apply),('jagniellonia',jagniellonia.apply),
        ('team_visibility',team_visibility.apply),('online_ui',online_ui.apply),('online_match',online_match.apply_match)]:
        result=recipe(merged);updates,details=result if isinstance(result,tuple) else (result,[])
        merged.update(updates);recipes.append({'recipe':name,'classes':sorted(updates),'details':details})
    compiled={path.name:path.read_bytes() for path in sorted(classes.glob('*.class'))}
    assert set(FAMILIES)=={name.split('$',1)[0].split('.')[0] for name in compiled}
    assert set(compiled).intersection(before)=={'CXOptions.class'},'Only scoped options helper replaces an existing helper'
    for name,data in compiled.items():
        assert data[:4]==b'\xca\xfe\xba\xbe' and struct.unpack_from('>H',data,6)[0]==47,name
        assert not any(tag in name for tag in ('QA','Probe','Stub','Fixture')),name
    merged.update(compiled)
    new_names=sorted(set(merged)-set(before))
    with zipfile.ZipFile(a.output/'code.pak','w') as archive:
        for info in infos:archive.writestr(info,merged[info.filename])
        for name in new_names:archive.writestr(name,merged[name])
    index=index_file.read_bytes()
    for name in new_names:
        assert name.encode('ascii') not in index.splitlines(),name
        index=index.rstrip(b'\r\n')+b'\r\n'+name.encode('ascii')+b'\r\n'
    (a.output/'code_inf.pak').write_bytes(index)
    with zipfile.ZipFile(a.output/'code.pak') as archive:
        assert archive.testzip() is None
        assert all(archive.read(n)==data for n,data in merged.items())
    report={'version':'v0.2.0-beta.1','baseline_code_sha256':BASE_SHA,
        'sources':{str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes()) for path in sources},
        'code_sha256':sha((a.output/'code.pak').read_bytes()),'index_sha256':sha(index),
        'changed_original_classes':sorted(name for name in before if before[name]!=merged[name]),
        'new_classes':new_names,'recipes':recipes,'class_format_major':47,
        'native_bridge_and_crlf_scr_required':True,'installed_game_modified':False,'runtime_tested':False}
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    print(json.dumps({key:report[key] for key in ['version','code_sha256','index_sha256','class_format_major']}))

if __name__=='__main__':main()
