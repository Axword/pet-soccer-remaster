"""Guarded one-call stock mesh-selection delta. No game files changed on import."""
from pathlib import Path
import hashlib,sys
HERE=Path(__file__).resolve().parent

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile,op

EXPECTED_BODY_SHA='bf75c95e72065cd3fa060fdee72d12e4bc75886d02ea083d8b30dee6ad80c302'
EXPECTED_PHYSICS_SHA='205d05cbb4814beb45a1ca23e76f7df6fd01e4ad442faafcbc5adffd95097de7'
def body(c,name,desc):
    raw=c.code(name,desc)[1];return raw[8:8+int.from_bytes(raw[4:8],'big')]

def apply(original):
    c=ClassFile(original['EAnimals.class']);name='SetAppearance';desc='(LMeshObject;III)V'
    before=body(c,name,desc)
    assert hashlib.sha256(before).hexdigest()==EXPECTED_BODY_SHA,'Unknown EAnimals.SetAppearance body'
    getmesh=c.member('EAnimals','GetMeshName','(I)Ljava/lang/String;',10)
    load=c.member('MeshObject','LoadMesh','(Ljava/lang/String;)V',10)
    pattern=b'\x2a\x1b'+op(184,getmesh)+op(182,load)
    assert before.count(pattern)==1
    replacement=b'\x2a\x1b'+op(184,c.member('CXAnimalIdentity','load','(LMeshObject;I)V',10))+b'\0\0\0'
    assert len(replacement)==len(pattern)==8
    skin=op(182,c.member('MeshObject','SetSkinElement','(Ljava/lang/String;I)V',10))
    skin_replacement=op(184,c.member('CXAnimalIdentity','skin','(LMeshObject;Ljava/lang/String;I)V',10))
    assert before.count(skin)==1
    c.edit(name,lambda code:bytes(code).replace(pattern,replacement).replace(skin,skin_replacement),desc)
    assert len(body(c,name,desc))==len(before)
    foot=ClassFile(original['FootBaller.class']);physics=body(foot,'UpdateExtents','()V')
    assert hashlib.sha256(physics).hexdigest()==EXPECTED_PHYSICS_SHA,'Unknown FootBaller.UpdateExtents body'
    # Replace only the null-field fallback's original bounds-read/allocation.
    # Per-species AI subclasses still supply their original explicit dimensions.
    block=physics[11:50]
    read=op(182,foot.member('MeshObject','GetMeshExtents','(LVector;LVector;)V',10))
    field=op(181,foot.member('FootBaller','vMeshExtents','LVector;'))
    assert len(block)==39 and block.count(read)==1 and block.endswith(field)
    replacement=b'\x2a\x2a'+op(184,foot.member('CXAnimalIdentity','physicsExtents','(LFootBaller;)LVector;',10))+field
    replacement+=bytes(len(block)-len(replacement))
    assert physics.count(block)==1
    foot.edit('UpdateExtents',lambda code:bytes(code).replace(block,replacement),'()V')
    assert len(body(foot,'UpdateExtents','()V'))==len(physics)
    return {'EAnimals.class':c.emit(),'FootBaller.class':foot.emit()}
