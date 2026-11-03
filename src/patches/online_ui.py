"""Guarded recipe for this current external PAK; no file I/O and no stock source."""
from pathlib import Path
import sys,struct,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile,op,append

NEW=['CXOnlineMenu','CXOnlineLobbyModel','CXOnlineVisibility','CXOnlineVisibility$Hidden']
EXPECTED={
 ('MenuMain.class','OnUICommand','(LUIWindow;I)V'):'137d872c43b2a3c44215e25b3b07657e6137cdae9cb3bbcd3fdeaddfd4e1b91f',
 ('MenuMain.class','OnInit','()V'):'6d091ff06db690be5716a9a0b846713fae266af4c264893b756933e945c9788c',
 ('SoccerMainMenuModule.class','<init>','()V'):'4d42199e2e39f8085295ca021d14830600d6f1c1a68f98d635800c5c48eec461',
 ('SoccerMainMenuModule.class','LoadUI','(I)V'):'d2aa52517c18774e80b7eb8fdea17195dd15e25281b389e6093a263de5da3741',
}
LIFECYCLE_EXPECTED={
 ('SoccerMainMenuModule.class','HideAllUIs','()V'):'de832dd0ea5b8762f69b43b3ecabe0eefaa394acb6442c85852b58e9a265c9a6',
 ('UserInterface.class','Hide','()V'):'eb474642538119c0db5e4ac0423a7cc3b959ac94c209bc0e39fdc49806d5e032',
 ('UserInterface.class','Show','()V'):'1d7f618b3c987b5e6d1c5507c642096b946c630fe88d8433c3d07680864f708e',
 ('SoccerUserInterface.class','Show','()V'):'da8eb2d971504340092de547f6620645cb4ba76b3ed9199dd1710b8f5a71d436',
}
def body(c,name,desc):
    raw=c.code(name,desc)[1];n=struct.unpack_from('>I',raw,4)[0];return raw[8:8+n]
def call(c,name,desc):return op(184,c.member('CXOnlineMenu',name,desc,10))

def apply(classes,compiled_dir=None):
    changed={}
    for filename in ['MenuMain.class','SoccerMainMenuModule.class']:
        c=ClassFile(classes[filename])
        for (owner,name,desc),expected in EXPECTED.items():
            if owner!=filename:continue
            before=body(c,name,desc)
            assert hashlib.sha256(before).hexdigest()==expected,(filename,name,'Current source differs from inspected GMWL PAK')
            if filename=='MenuMain.class' and name=='OnUICommand':
                # 16-byte prefix preserves tableswitch alignment in untouched stock body.
                after=b'\x2a\x2b\x1c'+call(c,'HandleMain','(LMenuMain;LUIWindow;I)Z')+b'\x99\x00\x0a\xb1'+b'\0'*6+before
            elif filename=='MenuMain.class':after=append(before,b'\x2a'+call(c,'MainInit','(LMenuMain;)V'))
            elif name=='<init>':
                assert before[20:24]==b'\x10\x14\xbd\x00', 'Expected current 20-entry tournament UI allocation'
                after=before[:21]+b'\x15'+before[22:]
            else:
                # 12-byte prefix preserves both existing tournament hook and original switch.
                after=b'\x2a\x1b'+call(c,'LoadUI','(LSoccerMainMenuModule;I)Z')+b'\x99\x00\x07\xb1'+b'\0'*3+before
            c.edit(name,lambda ignored:after,desc)
        changed[filename]=c.emit()
    for filename in ['SoccerMainMenuModule.class','UserInterface.class','SoccerUserInterface.class']:
        c=ClassFile(changed.get(filename,classes[filename]))
        for (owner,name,desc),expected in LIFECYCLE_EXPECTED.items():
            if owner!=filename:continue
            before=body(c,name,desc)
            assert hashlib.sha256(before).hexdigest()==expected,(filename,name,'Unknown lifecycle baseline')
            if name=='HideAllUIs':
                assert before[23:26]==b'\x1b\x10\x14'
                # Keep the existing null check and native virtual Hide. Only the bound changes.
                after=before[:24]+b'\x2a'+op(180,c.member('SoccerMainMenuModule','m_tUIs','[LSoccerUserInterface;'))+b'\xbe\xa1\xff\xe5\xb1'
            elif name=='Hide':
                after=append(before,b'\x2a'+op(184,c.member('CXOnlineVisibility','hidden','(LUserInterface;)V',10)))
            else:
                # Scoped no-op for ordinary offline screens; registered stale Show returns early.
                after=b'\x2a'+op(184,c.member('CXOnlineVisibility','show','(LUserInterface;)Z',10))+b'\x9a\x00\x04\xb1'+before
            c.edit(name,lambda ignored:after,desc)
        changed[filename]=c.emit()
    if compiled_dir is not None:
        for name in NEW:
            data=(Path(compiled_dir)/(name+'.class')).read_bytes()
            assert struct.unpack_from('>H',data,6)[0]==47,('Must target Java1.3',name)
            changed[name+'.class']=data
    return changed

def apply_code_inf(data):
    for name in NEW:
        entry=(name+'.class').encode('ascii')
        if entry not in data.splitlines():data=data.rstrip(b'\r\n')+b'\r\n'+entry+b'\r\n'
    return data
