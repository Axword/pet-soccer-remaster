"""One new native animal club, after stock identity hook and before selector visibility."""
from pathlib import Path
import hashlib,json,struct,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile,op,append
EXPECTED=json.loads((HERE/'registration-fingerprints.json').read_text())


def sha(data):return hashlib.sha256(data).hexdigest()
def body(c,name,desc):
    data=c.code(name,desc)[1];return data[8:8+struct.unpack_from('>I',data,4)[0]]


def apply(entries):
    assert 'CXJagniellonia.class' not in entries,'New club already applied'
    updates={}
    classes=('EAnimals','ETeams','CoreLogic','MenuChooseTeam','CXGMWProfile','TeamData')
    for classname in classes:
        c=ClassFile(entries[classname+'.class'])
        untouched={(c.ref(m[1]),c.ref(m[2])):list(m[3]) for m in c.methods};edited=set()
        for name,digest in EXPECTED[classname].items():
            desc='(I)I' if name=='Map' else '(I)Z' if name=='Selected' else '()Z' if name=='IsAvailable' else '()V'
            old=body(c,name,desc);assert sha(old)==digest,(classname,name,'Unknown current method')
            new=old
            if classname in ('EAnimals','ETeams','CoreLogic'):
                method={'EAnimals':'Animals','ETeams':'Teams','CoreLogic':'Maps'}[classname]
                new=append(old,op(184,c.member('CXJagniellonia',method,'()V',10)))
            elif classname=='CXGMWProfile':
                value=42 if name=='Map' else 58
                # Eight bytes: original branch alignment/control flow preserved.
                new=b'\x1a\x10'+bytes([value])+b'\xa0\x00\x05'+(b'\x1a' if name=='Map' else b'\x04')+b'\xac'+old
            elif classname=='MenuChooseTeam' and name=='<init>':
                pattern=b'\x10\x10'+op(189,c.clazz('TeamData'));assert old.count(pattern)==1
                new=old.replace(pattern,b'\x10\x11'+op(189,c.clazz('TeamData')))
            elif classname=='MenuChooseTeam':
                extra=b'\x2a'+op(180,c.member('MenuChooseTeam','tTeams','[LTeamData;'))+b'\x10\x10\x10\x3a'+op(184,c.member('ETeams','GetTeamData','(I)LTeamData;',10))+b'\x53'
                new=append(old,extra)
            elif classname=='TeamData':
                new=b'\x2a'+op(180,c.member('TeamData','m_nAnimalType','I'))+b'\x10\x3a\xa0\x00\x06\x04\xac\x00'+old
            c.edit(name,lambda _,data=new:data,desc);edited.add((name,desc))
        if classname=='EAnimals':
            name='SetAppearance';desc='(LMeshObject;III)V';old=body(c,name,desc)
            pattern=op(184,c.member('CXAnimalIdentity','load','(LMeshObject;I)V',10))
            assert old.count(pattern)==1,'Apply stock identity hook before Jagniellonia'
            replacement=op(184,c.member('CXJagniellonia','load','(LMeshObject;I)V',10))
            c.edit(name,lambda code:bytes(code).replace(pattern,replacement),desc);edited.add((name,desc))
        for method in c.methods:
            key=c.ref(method[1]),c.ref(method[2])
            if key not in edited:assert method[3]==untouched[key],(classname,key,'Unowned method changed')
        updates[classname+'.class']=c.emit()
    return updates
