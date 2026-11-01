"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

NEW=['CXKnockout','CXKnockoutSetup','CXKnockoutMenu']

OWNED={
 'MenuMultiplayer.class':[('OnUICommand','(LUIWindow;I)V'),('OnInit','()V'),('Show','()V')],
 'SoccerMainMenuModule.class':[('<init>','()V'),('LoadUI','(I)V'),('ShowLoadingScreen','()V')],
 'MenuPreMatch.class':[('OnBack','()V')],
 'Match.class':[('Update','()V')],
 'SoccerModule.class':[('ShowMenuEnd','()V')],
}

def sha(b):return hashlib.sha256(b).hexdigest()

def call(c,n,d):return op(184,c.member('CXKnockout',n,d,10))

def body(c,n,d):
 a=c.code(n,d)[1];return a[8:8+struct.unpack_from('>I',a,4)[0]]

def apply(classes, baseline_classes, compiled_dir):
 reference={n:baseline_classes[n] for n in OWNED}
 updates={}
 for filename,methods in OWNED.items():
  c=C(classes[filename]);original=C(reference[filename])
  for name,desc in methods:
   before=body(original,name,desc);current=body(c,name,desc)
   if filename=='MenuMultiplayer.class' and name=='OnUICommand':
    after=b'\x2a\x2b\x1c'+call(c,'HandleSetup','(LMenuMultiplayer;LUIWindow;I)Z')+b'\x99\x00\x0a\xb1'+b'\0'*6+before
   elif filename=='MenuMultiplayer.class' and name=='OnInit':
    after=append(before,b'\x2a'+call(c,'SetupInit','(LMenuMultiplayer;)V'))
   elif filename=='MenuMultiplayer.class' and name=='Show':
    assert original.ref(struct.unpack_from('>H',before,174)[0])=='&MenuTitleMultiplayer&'
    assert before[173]==19 and before[176]==184
    after=before[:173]+b'\x2a'+call(c,'SetupTitle','(LMenuMultiplayer;)Ljava/lang/String;')+b'\0\0'+before[179:]
   elif filename=='SoccerMainMenuModule.class' and name=='<init>':
    assert before[20:22]==b'\x10\x12'
    after=before[:21]+b'\x14'+before[22:]
   elif filename=='SoccerMainMenuModule.class' and name=='LoadUI':
    after=b'\x2a\x1b'+call(c,'LoadUI','(LSoccerMainMenuModule;I)Z')+b'\x99\x00\x07\xb1'+b'\0'*3+before
   elif filename=='SoccerMainMenuModule.class' and name=='ShowLoadingScreen':
    after=append(before,call(c,'FixReturnUI','()V'))
   elif filename=='MenuPreMatch.class':
    after=b'\x2a'+call(c,'PreMatchBack','(LMenuPreMatch;)Z')+b'\x99\x00\x08\xb1'+b'\0'*4+before
   elif filename=='Match.class':
    assert before[137]==178 and before[140:143]==b'\x99\x00\x2d' and before[152:155]==b'\x9e\x00\x21'
    after=before[:137]+call(c,'AllowGoldenGoal','()Z')+b'\x99\x00\x2d'+b'\0'*12+before[155:]
   elif filename=='SoccerModule.class':
    after=call(c,'Completed','()V')+before
   else:raise AssertionError((filename,name))
   if current==after:continue
   assert current==before,(filename,name,'Owned method changed since optimized baseline')
   a=c.code(name,desc);raw=a[1];n=len(before)
   if len(after)==n:a[1]=raw[:8]+after+raw[8+n:]
   else:c.edit(name,lambda b:after,desc)
  emitted=c.emit()
  if emitted!=classes[filename]:updates[filename]=emitted
 for name in NEW:
  b=(pathlib.Path(compiled_dir)/(name+'.class')).read_bytes()
  assert struct.unpack_from('>H',b,6)[0]==47,('Wrong JVM target',name)
  if classes.get(name+'.class')!=b:updates[name+'.class']=b
 return updates

def apply_code_inf(data):
 for name in NEW:
  entry=(name+'.class').encode('ascii')
  if entry not in data.splitlines():data=data.rstrip(b'\r\n')+b'\r\n'+entry+b'\r\n'
 return data
