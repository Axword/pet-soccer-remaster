"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append
from src.patches.console_guard import instructions

H = pathlib.Path(__file__).resolve().parent

ALLOWED_SPECIES=list(range(13))+list(range(37,58))

HIDDEN=[i for i in range(13,86) if i not in ALLOWED_SPECIES]

REPS=[37,44,51]

ALLOWED_MAPS=list(range(21))+[38,40,41]

OLD_REPS=[19,30,37,44,51,58,65,73]

OWNED={'MenuChooseTeam.class':[('<init>','()V'),('OnCreate','()V')],
 'EAnimals.class':[('<clinit>','()V')],
 'ETeams.class':[('<clinit>','()V'),('InitTeamData','()V'),('GetHomeField','(I)I')],
 'CoreLogic.class':[('<clinit>','()V'),('GetNextLevel','()I')],
 'SoccerModule.class':[('AddFootBaller','(IIILjava/lang/String;)LAIFootBaller;')],
 'CXKnockout.class':[('Seed','(LCXKnockoutSetup;)V')]}

def sha(b):return hashlib.sha256(b).hexdigest()

def integer(i):return bytes([3+i]) if -1<=i<=5 else b'\x10'+struct.pack('b',i)

def body(c,n,d):
 r=c.code(n,d)[1];return r[8:8+struct.unpack_from('>I',r,4)[0]]

def strings(v):
 if isinstance(v,str):return [v]
 if isinstance(v,list):return [s for item in v for s in strings(item)]
 if isinstance(v,dict):return [s for item in v.values() for s in strings(item)]
 return []

def norm(s):return s.replace('\\','/').lower()

def asset_string(s):
 s=norm(s);return (s.startswith('data/') or s.endswith('.3da')) and not s.endswith('/')

def allowed_paths(snapshot,owner):
 out=[]
 if owner=='EAnimals.class':
  for name,arr in snapshot['EAnimals'].items():
   if name=='CXVoice':continue
   for i in ALLOWED_SPECIES:out.extend(strings(arr[i]))
 elif owner=='ETeams.class':
  for i in ALLOWED_SPECIES:out.extend(strings(snapshot['teamAPI'][i]))
 elif owner=='CoreLogic.class':
  for name,arr in snapshot['CoreLogic'].items():
   if name in ('sLevelFileNames','sLevelNames','sLevelMusic','sLevelLoopSounds'):
    for i in ALLOWED_MAPS:out.extend(strings(arr[i]))
   else:out.extend(strings(arr))
 return {norm(s) for s in out if asset_string(s)}

def scrub(c,owner,snapshot):
 allowed=allowed_paths(snapshot,owner);changes=[]
 # Original scalar constants (e.g. the locked-team Unavail.3da placeholder)
 # are outside the species arrays and must survive this profile unchanged.
 for flags,n,d,attrs in c.fields:
  if c.ref(d)!='Ljava/lang/String;':continue
  for key,value in attrs:
   if c.ref(key)=='ConstantValue':
    text=c.ref(struct.unpack('>H',value)[0])
    if asset_string(text):allowed.add(norm(text))
 # Preserve actual engine API paths used by unchanged methods. The old
 # m_sScrFiles arrays are historical; GetAnimalScrFile deliberately returns
 # AIFootballer.scr/AIGoalkeeper.scr instead, and those files must not be scrubbed.
 initializers={'EAnimals.class':{'<clinit>'},'ETeams.class':{'InitTeamData'},'CoreLogic.class':{'<clinit>'}}[owner]
 for method in c.methods:
  if c.ref(method[1]) in initializers:continue
  for key,raw in method[3]:
   if c.ref(key)!='Code':continue
   code=raw[8:8+struct.unpack_from('>I',raw,4)[0]]
   for offset,opcode in instructions(code):
    if opcode not in (18,19):continue
    index=code[offset+1] if opcode==18 else struct.unpack_from('>H',code,offset+1)[0]
    if c.cp[index][0]==8:
     text=c.ref(index)
     if asset_string(text):allowed.add(norm(text))
 for i,entry in enumerate(c.cp):
  if not entry or entry[0]!=1:continue
  s=entry[1]
  if not asset_string(s) or norm(s) in allowed:continue
  low=norm(s)
  if owner=='ETeams.class':replacement='data/menu/logos/T_Logo_Robots.png'
  elif low.endswith('.3da'):replacement='robocik.3da' if '/' not in low else 'data/meshes/animals/robocik.3da'
  elif low.startswith('data/sounds/'):
   replacement='data/sounds/commentary_pl/083.wav' if low.endswith('.wav') else 'data/sounds/commentary_pl/083'
  elif low.endswith('.png'):replacement='data/textures/tshirts/robocik_01.png'
  elif low.endswith('.scr'):replacement='data\\Animals_scr\\robo.scr'
  elif low.endswith('.map'):replacement=snapshot['CoreLogic']['sLevelFileNames'][0]
  else:raise AssertionError(('Unknown asset constant',owner,s))
  encoded=replacement.encode('utf8');c.cp[i]=(1,replacement,b'\x01'+struct.pack('>H',len(encoded))+encoded);changes.append((s,replacement))
 return changes

def apply(classes, baseline_classes, snapshot, compiled_dir):
 reference={n:baseline_classes[n] for n in OWNED}
 updates={}
 for filename,methods in OWNED.items():
  c=C(classes[filename]);ref=C(reference[filename])
  if filename in ('EAnimals.class','ETeams.class','CoreLogic.class'):scrub(c,filename,snapshot)
  for name,desc in methods:
   before=body(ref,name,desc);current=body(c,name,desc)
   call=lambda method,d='()V':op(184,c.member('CXGMWProfile',method,d,10))
   if filename=='MenuChooseTeam.class' and name=='<init>':
    old=integer(20)+op(189,c.clazz('TeamData'));new=integer(15)+op(189,c.clazz('TeamData'));assert before.count(old)==1;after=before.replace(old,new)
   elif filename=='MenuChooseTeam.class':
    field=c.member('MenuChooseTeam','tTeams','[LTeamData;');get=c.member('ETeams','GetTeamData','(I)LTeamData;',10)
    def tail(reps):return b''.join(b'\x2a'+op(180,field)+integer(i)+integer(rep)+op(184,get)+b'\x53' for i,rep in enumerate(reps,12))+b'\xb1'
    old=tail(OLD_REPS);assert before.endswith(old);after=before[:-len(old)]+tail(REPS)
   elif filename=='EAnimals.class':after=append(before,call('Animals'))
   elif filename=='ETeams.class' and name=='<clinit>':after=append(before,call('TeamStats'))
   elif filename=='ETeams.class' and name=='InitTeamData':after=append(before,call('Teams'))
   elif filename=='ETeams.class':after=b'\x1a'+call('Species','(I)I')+b'\x3b\0\0\0'+before
   elif filename=='CoreLogic.class' and name=='<clinit>':after=append(before,call('Maps'))
   elif filename=='CoreLogic.class':
    assert len(before)==4 and before[0]==178 and before[-1]==172;after=before[:-1]+call('Map','(I)I')+b'\xac'
   elif filename=='SoccerModule.class':after=b'\x1c'+call('Species','(I)I')+b'\x3d\0\0\0'+before
   elif filename=='CXKnockout.class':after=b'\x2a'+call('Seed','(LCXKnockoutSetup;)V')+b'\xb1'
   else:raise AssertionError((filename,name))
   if current==after:continue
   assert current==before,(filename,name,'Target method changed; audit first')
   c.edit(name,lambda _:after,desc)
  emitted=c.emit()
  if emitted!=classes[filename]:updates[filename]=emitted
 helper=(pathlib.Path(compiled_dir)/'CXGMWProfile.class').read_bytes();assert struct.unpack_from('>H',helper,6)[0]==47
 if classes.get('CXGMWProfile.class')!=helper:updates['CXGMWProfile.class']=helper
 return updates

def apply_code_inf(data):
 entry=b'CXGMWProfile.class'
 return data if entry in data.splitlines() else data.rstrip(b'\r\n')+b'\r\n'+entry+b'\r\n'
