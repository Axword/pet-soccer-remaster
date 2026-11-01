"""Guarded human menu-preview repair for the reviewed beta2 mod baseline.

Reads an external game archive; writes a NEW isolated output directory.
No original game implementation, assets or compiled classes are distributed.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zipfile

from tools.classfile import ClassFile,op,append

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(data):return hashlib.sha256(data).hexdigest()
def body(c,name,desc):
    raw=c.code(name,desc)[1]
    return raw[8:8+struct.unpack_from('>I',raw,4)[0]]
def call(c,name,desc):return op(184,c.member('CXHumanPreview',name,desc,10))

EXPECTED={
  "MenuAnimal.class": {
    "LoadMesh(Ljava/lang/String;)V": "82aade7a6c170b1edeaefa477bd1850401253095a501f48167db1d9ed2fe455e",
    "SetHappiness(Z)V": "3d54d8d8295e9dad161b764df06fa8a95a9aab940c397ec78989cadb79eb6e9f",
    "Reset()V": "0e7d2b2f788c6f6087cf24651a10ceb000836646b77d8be96c7b6fa6e88f9591",
    "OnDestinationPos()V": "603b47e97943ae7bfa082c86832fdf720e623ef02abf62df379e4def39272717"
  },
  "SoccerMenuShowObjectModule.class": {
    "SetFootballer(I)V": "31146b6c8fab21b5fcedb9af1a95093d78e0ef955ea9260b9ac61647a2544380",
    "ContinueSetFootballer()V": "3fef59b3b2543b8067166fa553b410b0a4b63e3d8a4de264666e61aa57c629c5",
    "ResetScene()V": "ae6a520b5d24ed102835d6d083ed9694ce5335743adfd44141063fe023fbb2d5",
    "Deactivate()V": "008227c4692dcd090927730f2713e8854e03b2901e7f46d3f082cae570d6ac4c",
    "OnDeactivate()V": "9a3fb50ea24d8095266ff13f59dafa78fce98328ac11a2a2cbe4c6543dc07b7b",
    "OnActivate()V": "7e58fa9c5d1660751ab6b007643e4eedc745ee6ce4ed1d6c472709bf34da1f8b",
    "Unload()V": "2e04cf6fa68fa3f3b0320ddb9fc0a5b166b39d233b5279256245d4a096fb0fd1",
    "SetFootballerCup(II)V": "894a03649bbeadf1e88c1810f9d9735309547e56d3c5df7687156cf56b113aeb",
    "SetFootballerInstant(II)V": "182cb50cfccb8e7911806483e1cf21d839606056b82b7cf2281247f2009cfbef"
  }
}

def apply(classes,helper,expected=None):
    assert 'CXHumanPreview.class' not in classes,'Already patched; use the reviewed beta2 input'
    assert struct.unpack_from('>H',helper,6)[0]==47
    helper_class=ClassFile(helper)
    assert helper_class.ref(struct.unpack_from('>H',helper_class.bodyhead,2)[0])=='CXHumanPreview','Wrong compiled helper'
    expected=EXPECTED if expected is None else expected
    assert expected,'Supply the reviewed beta2 fingerprints'
    changes=[];updates={}
    for filename,methods in expected.items():
        c=ClassFile(classes[filename])
        for signature,digest in methods.items():
            name,tail=signature.split('(',1);desc='('+tail
            before=body(c,name,desc)
            assert sha(before)==digest,(filename,signature,'Input method changed')
            if filename=='MenuAnimal.class':
                if name=='LoadMesh':
                    assert before[:2]==b'\x2a\x2b' and before[2]==183
                    after=before[:5]+b'\x2a'+call(c,'Configure','(LMenuAnimal;)V')+before[5:]
                elif name=='SetHappiness':
                    after=b'\x2a\x1b'+call(c,'Happiness','(LMenuAnimal;Z)V')+b'\xb1'
                elif name=='Reset':after=append(before,b'\x2a'+call(c,'Reset','(LMenuAnimal;)V'))
                elif name=='OnDestinationPos':after=b'\x2a'+call(c,'FaceForPreview','(LMenuAnimal;)V')+before
                else:raise AssertionError(signature)
            else:
                prefix=lambda method:b'\x2a'+call(c,method,'(LSoccerMenuShowObjectModule;)V')
                if name=='SetFootballer':
                    target=op(182,c.member('GameObject','CallMethodIn','(Ljava/lang/String;F)V',10))
                    assert before.count(target)==1
                    replacement=call(c,'Schedule','(LSoccerMenuShowObjectModule;Ljava/lang/String;F)V')
                    modified=before.replace(target,replacement)
                    immediate=op(182,c.member('SoccerMenuShowObjectModule','ContinueSetFootballer','()V',10))
                    assert modified.count(immediate)==1
                    modified=modified.replace(immediate,call(c,'Immediate','(LSoccerMenuShowObjectModule;)V'))
                    after=b'\x2a\x1b'+call(c,'BeforeSelection','(LSoccerMenuShowObjectModule;I)V')+modified
                elif name=='ContinueSetFootballer':after=prefix('Deferred')+b'\xb1'
                elif name in ('ResetScene','Unload'):after=prefix('Cancel')+before
                elif name in ('Deactivate','OnDeactivate'):after=prefix('Suspend')+before
                elif name=='OnActivate':after=append(before,prefix('Resume'))
                elif name=='SetFootballerCup':after=append(before,prefix('FinishCup'))
                elif name=='SetFootballerInstant':after=append(before,prefix('FinishInstant'))
                else:raise AssertionError(signature)
            c.edit(name,lambda _,value=after:value,desc)
            changes.append({'class':filename,'method':signature,'before_sha256':digest,'after_sha256':sha(after)})
        updates[filename]=c.emit()
    updates['CXHumanPreview.class']=helper
    return updates,changes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--code-index',type=Path,required=True)
    p.add_argument('--helper',type=Path,default=ROOT/'build/java/CXHumanPreview.class')
    p.add_argument('--fingerprints',type=Path,default=HERE/'human_preview_fingerprints.json')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert not a.output.exists(),'Output must be new'
    with zipfile.ZipFile(a.input) as archive:
        infos=archive.infolist();classes={i.filename:archive.read(i) for i in infos}
    updates,methods=apply(classes,a.helper.read_bytes(),json.loads(a.fingerprints.read_text()))
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.output/'code.pak','w') as archive:
        for info in infos:archive.writestr(info,updates.get(info.filename,classes[info.filename]))
        for name in sorted(set(updates)-set(classes)):
            info=zipfile.ZipInfo(name,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,updates[name])
    index=a.code_index.read_bytes()
    assert b'CXHumanPreview.class' not in index.splitlines()
    (a.output/'code_inf.pak').write_bytes(index.rstrip(b'\r\n')+b'\r\nCXHumanPreview.class\r\n')
    with zipfile.ZipFile(a.output/'code.pak') as archive:
        assert all(archive.read(n)==data for n,data in classes.items() if n not in updates)
    receipt={'input_sha256':sha(a.input.read_bytes()),'output_sha256':sha((a.output/'code.pak').read_bytes()),
             'changed_classes':sorted(updates),'methods':methods,'models_ini_textures_changed':False,
             'runtime_preview_test_required':True}
    (a.output/'manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='methods'}))

if __name__=='__main__':main()
