"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

SPECS=[
 # Update diagnostic result is POPped; no consumer exists.
 ('AIMatch.class','Update','()V',[(71,116)],
  'c4342010aa2baa8804b1ca38586955ee922d6638c1091393127b7f06dc6e49f3'),
 # These local variables start null and are never read anywhere in OnFrame.
 ('AIFootBaller.class','OnFrame','()V',[(115,142),(189,216),(271,296)],
  '94416e269318d39385e191f9524bd7e6fafe7e9c2a770cbb578be84427f9da04'),
]

def sha(b):return hashlib.sha256(b).hexdigest()

def rewrite(c,name,desc,ranges):
 a=c.code(name,desc);raw=a[1];n=struct.unpack_from('>I',raw,4)[0];body=bytearray(raw[8:8+n])
 for start,end in ranges:
  # Branch over the old pure-expression span. Its unreachable bytes become
  # NOPs; unchanged offsets preserve all original exception/debug positions.
  body[start:end]=b'\xa7'+struct.pack('>h',end-start)+b'\x00'*(end-start-3)
 a[1]=raw[:8]+body+raw[8+n:]
 return c.emit()

def apply(classes):
 updates={}
 for filename,name,desc,ranges,expected in SPECS:
  c=C(classes[filename]);raw=c.code(name,desc)[1];body=raw[8:8+struct.unpack_from('>I',raw,4)[0]]
  already=all(body[a:b]==b'\xa7'+struct.pack('>h',b-a)+b'\0'*(b-a-3) for a,b in ranges)
  if already:continue
  assert sha(raw)==expected,(filename,name,'method changed: audit before applying',sha(raw))
  updates[filename]=rewrite(c,name,desc,ranges)
 return updates
