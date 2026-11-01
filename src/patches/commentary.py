"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

def apply(classes):
 updates={};c=C(classes['CXSupport.class'])
 for name,desc in [('BeforeCommentary','(LCommentator;Ljava/lang/String;)V'),('CommentaryVisual','(LCommentator;)V')]:
  if not any(c.ref(m[1])==name for m in c.methods):c.methods.append([0x109,c.add(1,name),c.add(1,desc),[]])
 updates['CXSupport.class']=c.emit();c=C(classes['Commentator.class'])
 call=lambda name,desc:op(184,c.member('CXSupport',name,desc,10))
 prefix=b'\x2a\x2b'+call('BeforeCommentary','(LCommentator;Ljava/lang/String;)V')+b'\x00\x00\x00'
 raw=c.code('Say')[1];n=struct.unpack_from('>I',raw,4)[0]
 if not raw[8:8+n].startswith(prefix):c.edit('Say',lambda b:prefix+b)
 suffix=b'\x2a'+call('CommentaryVisual','(LCommentator;)V')+b'\xb1'
 raw=c.code('PlayTalkAnim')[1];n=struct.unpack_from('>I',raw,4)[0]
 if not raw[8:8+n].endswith(suffix):c.edit('PlayTalkAnim',lambda b:append(b,suffix[:-1]))
 updates['Commentator.class']=c.emit()
 return {n:b for n,b in updates.items() if classes[n]!=b}
