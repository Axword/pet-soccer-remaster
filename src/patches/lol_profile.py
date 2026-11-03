"""Restore exactly one seven-champion club over the reviewed GMW+special-ball input."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zipfile
sys.dont_write_bytecode=True
PUBLIC=Path(__file__).resolve().parents[2]
if '--repo-root' in sys.argv:
    at=sys.argv.index('--repo-root');assert at+1<len(sys.argv),'--repo-root needs a path'
    PUBLIC=Path(sys.argv[at+1]).resolve()
if (PUBLIC/'tools/classfile.py').is_file():sys.path.insert(0,str(PUBLIC))
try:
    from tools.classfile import ClassFile,op,append
except ModuleNotFoundError:
    raise SystemExit('Run inside the public source repository, or pass --repo-root PATH containing tools/classfile.py')

def sha(b):return hashlib.sha256(b).hexdigest()
def body(c,name,desc):
    raw=c.code(name,desc)[1];return raw[8:8+struct.unpack_from('>I',raw,4)[0]]
EXPECTED_PROFILE='4639d6bcbad44e25b2ce4d0c9ac58e9d46c8d01fda48b731e5d099af21518568'
EXPECTED_MENU={'<init>':'913b09aa95649c0fd6385ca81923ff835741da1c07f4be667ddb556def71eee3','OnCreate':'48d34b268dc9ab2bf9acd18ec85d6d2928346c06137c1efb810887a7f8f16ce4'}
EXPECTED_SPECIAL='cfbfdb22b379a298fb5877d2e2e67116e4c465ee6197e7f234de13bff8c3f073'
EXPECTED_PREVIEW='1ad7fd35221e978d2fa83e7a4fecef351ce1531cc4ea269321dec981e9fdeabd'

def apply(entries,compiled):
    assert 'CXLoLProfile.class' not in entries,'Already patched'
    assert sha(entries['CXGMWProfile.class'])==EXPECTED_PROFILE,'Unreviewed profile input'
    assert sha(entries['CXSpecialBall.class'])==EXPECTED_SPECIAL,'Accepted special-ball guard required'
    assert sha(entries['CXHumanPreview.class'])==EXPECTED_PREVIEW,'Unreviewed human preview input'
    updates={};changes=[]
    c=ClassFile(entries['MenuChooseTeam.class'])
    for name,digest in EXPECTED_MENU.items():
        before=body(c,name,'()V');assert sha(before)==digest,(name,'Input method changed')
        if name=='<init>':
            old=b'\x10\x0f'+op(189,c.clazz('TeamData'));assert before.count(old)==1
            after=before.replace(old,b'\x10\x10'+op(189,c.clazz('TeamData')))
        else:
            tail=b'\x2a'+op(180,c.member('MenuChooseTeam','tTeams','[LTeamData;'))+b'\x10\x0f\x10\x1e'+op(184,c.member('ETeams','GetTeamData','(I)LTeamData;',10))+b'\x53'
            after=append(before,tail)
        c.edit(name,lambda _,value=after:value,'()V')
        changes.append({'class':'MenuChooseTeam.class','method':name+'()V','before_sha256':digest,'after_sha256':sha(after)})
    updates['MenuChooseTeam.class']=c.emit()
    for name in ['CXGMWProfile','CXLoLProfile','CXHumanPreview']:
        data=(Path(compiled)/(name+'.class')).read_bytes();helper=ClassFile(data)
        assert struct.unpack_from('>H',data,6)[0]==47
        assert helper.ref(struct.unpack_from('>H',helper.bodyhead,2)[0])==name
        updates[name+'.class']=data
    return updates,changes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--code-index',type=Path,required=True)
    p.add_argument('--compiled',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repo-root',type=Path,help='Public source root; autodetected when this recipe is under src/patches/')
    a=p.parse_args();assert not a.output.exists(),'Output must be new'
    with zipfile.ZipFile(a.input) as z:infos=z.infolist();entries={i.filename:z.read(i) for i in infos}
    updates,methods=apply(entries,a.compiled)
    index=a.code_index.read_bytes();assert b'CXLoLProfile.class' not in index.splitlines()
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.output/'code.pak','w') as z:
        for i in infos:z.writestr(i,updates.get(i.filename,entries[i.filename]))
        for name in sorted(set(updates)-set(entries)):
            i=zipfile.ZipInfo(name,(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,updates[name])
    (a.output/'code_inf.pak').write_bytes(index.rstrip(b'\r\n')+b'\r\nCXLoLProfile.class\r\n')
    with zipfile.ZipFile(a.output/'code.pak') as z:
        assert all(z.read(n)==data for n,data in entries.items() if n not in updates)
    report={'input_sha256':sha(a.input.read_bytes()),'output_sha256':sha((a.output/'code.pak').read_bytes()),'changed_classes':sorted(updates),'methods':methods,'special_ball_guard_unchanged':True,'other_archive_entries_unchanged':True,'selected_species':list(range(13))+list(range(30,58)),'visible_representatives':[37,44,51,30],'visible_teams':16,'new_home_map':39,'club':'Real Runeterra','roster':['Warwick','Nasus','Ahri','Garen','Jinx','Teemo','Blitzcrank'],'native_runtime_required':True,'asset_delivery_required':True}
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
