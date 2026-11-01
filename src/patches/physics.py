"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

NATIVES=[('PhysicsTerrainHeight','(LGameObject;FF)F'),('PhysicsSanitizePosition','(LBall;LVector;)LVector;'),('PhysicsGuardBall','(LBall;)Z'),('PhysicsQAStep','(I)Z')]

def apply(classes):
 """Return two class replacements for an already integrated class dictionary."""
 updates={};report={'terrain_calls':{},'guarded_methods':['OnPhysicsUpdate','CheckGoal','OnFrame'],'sanitize_methods':['SetPosition'],'native_methods':NATIVES}
 c=C(classes['CXSupport.class'])
 for name,desc in NATIVES:
  existing=[m for m in c.methods if c.ref(m[1])==name and c.ref(m[2])==desc]
  if not existing:c.methods.append([0x109,c.add(1,name),c.add(1,desc),[]])
 updates['CXSupport.class']=c.emit()
 c=C(classes['Ball.class'])
 old=op(182,c.member('GameObject','TerrainHeight','(FF)F',10))
 new=op(184,c.member('CXSupport','PhysicsTerrainHeight','(LGameObject;FF)F',10))
 for m in list(c.methods):
  attrs=[a for a in m[3] if c.ref(a[0])=='Code']
  if not attrs:continue
  a=attrs[0];b=a[1];length=struct.unpack_from('>I',b,4)[0];body=b[8:8+length];count=body.count(old)
  if count:
   # Identical opcode width and effective stack consumption: no offset changes.
   a[1]=b[:8]+body.replace(old,new)+b[8+length:]
   report['terrain_calls'][c.ref(m[1])]=count
 assert sum(report['terrain_calls'].values())>=4,report
 for name in report['guarded_methods']:
  invoke=op(184,c.member('CXSupport','PhysicsGuardBall','(LBall;)Z',10))
  c.edit(name,lambda b:b'\x2a'+invoke+b'\x99\x00\x04\xb1'+b)
 invoke=op(184,c.member('CXSupport','PhysicsSanitizePosition','(LBall;LVector;)LVector;',10))
 c.edit('SetPosition',lambda b:b'\x2a\x2b'+invoke+b'\x4c\x00\x00'+b)
 updates['Ball.class']=c.emit()
 return updates
