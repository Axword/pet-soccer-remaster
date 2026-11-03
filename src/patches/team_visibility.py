"""Guarded selector-only hooks; keep all definitions, saves, unlocks and other methods."""
from pathlib import Path
import argparse, hashlib, json, struct, sys, zipfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile, op

EXPECTED={
    ('MenuChooseTeam','RefreshAvailableTeams','()V'): '28189f82c72b7abed408d1d5487d3c80109ee99b85d4540e77b58b01cd122567',
    ('MenuChooseTeam','GetTeams','()[LTeamData;'): '0256bbf2ee9b049b72c52c383a0ffd7278c47d2cd9bc11d1a1fb60fe8bf4f524',
    ('MenuMultiplayer','Show','()V'): 'aeae928bc3153efad2ed0a1e485a85ec6656ff6ce003a6e7e7ff6af791fc4835',
}


def sha(data): return hashlib.sha256(data).hexdigest()
def body(c,name,desc):
    raw=c.code(name,desc)[1]
    return raw[8:8+struct.unpack_from('>I',raw,4)[0]]


def apply(entries,compiled=None):
    assert 'CXTeamVisibility.class' not in entries, 'Content gate already present'
    updates,changes={},[]
    for classname in ('MenuChooseTeam','MenuMultiplayer'):
        c=ClassFile(entries[classname+'.class'])
        untouched={(c.ref(m[1]),c.ref(m[2])):list(m[3]) for m in c.methods}
        edited=set()
        for (owner,name,desc),digest in EXPECTED.items():
            if owner!=classname:continue
            before=body(c,name,desc)
            assert sha(before)==digest, (owner,name,'Unreviewed selector method')
            helper='Refresh' if owner=='MenuChooseTeam' else 'PrepareMultiplayer'
            prefix=b'\x2a'+op(184,c.member('CXTeamVisibility',helper,'(L'+owner+';)V',10))
            assert len(prefix)==4 # keeps original switch alignment and all branch offsets
            c.edit(name,lambda code,p=prefix:p+bytes(code),desc)
            edited.add((name,desc))
            changes.append({'class':owner+'.class','method':name+desc,'before_sha256':digest,'after_sha256':sha(body(c,name,desc)),'prefix_only_bytes':4})
        for m in c.methods:
            key=c.ref(m[1]),c.ref(m[2])
            if key not in edited:assert m[3]==untouched[key], (classname,key,'Unowned attributes changed')
        updates[classname+'.class']=c.emit()
    if compiled is not None:
        data=(Path(compiled)/'CXTeamVisibility.class').read_bytes()
        assert struct.unpack_from('>H',data,6)[0]==47,'Java1.3 output required'
        helper=ClassFile(data)
        assert helper.ref(struct.unpack_from('>H',helper.bodyhead,2)[0])=='CXTeamVisibility'
        updates['CXTeamVisibility.class']=data
    return updates,changes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--code-index',type=Path,required=True)
    parser.add_argument('--compiled',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists(),'Fresh candidate output required'
    with zipfile.ZipFile(args.input) as archive:
        infos=archive.infolist();entries={i.filename:archive.read(i) for i in infos}
    updates,changes=apply(entries,args.compiled)
    index=args.code_index.read_bytes()
    assert b'CXTeamVisibility.class' not in index.splitlines()
    index=index.rstrip(b'\r\n')+b'\r\nCXTeamVisibility.class\r\n'
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.output/'code.pak','w') as archive:
        for info in infos:archive.writestr(info,updates.get(info.filename,entries[info.filename]))
        for name in sorted(set(updates)-set(entries)):archive.writestr(name,updates[name])
    (args.output/'code_inf.pak').write_bytes(index)
    with zipfile.ZipFile(args.output/'code.pak') as archive:
        assert all(archive.read(n)==data for n,data in entries.items() if n not in updates)
    report={'format':'PET-SOCCER-TEAM-VISIBILITY-LOCAL-1','input_code_sha256':sha(args.input.read_bytes()),
            'output_code_sha256':sha((args.output/'code.pak').read_bytes()),'index_sha256':sha(index),
            'changed_classes':sorted(updates),'methods':changes,'unowned_methods_preserved':True,
            'player_save_or_unlock_changes':False,'default_hidden':[30,37,44,51,58],
            'new_animal_58_not_gated':False,'native_options_and_online_sources_required':True,
            'native_runtime_verified':False,'installed_game_changed':False}
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__': main()
