"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

EXPECTED='f352dd810c70809463d7f86b00a5c14c660ba29c79cf1da8936def513e0118cd'

def sha(b):return hashlib.sha256(b).hexdigest()

def apply(classes):
 c=C(classes['AITeam.class']);a=c.code('UpdateGame','()V');raw=a[1];n=struct.unpack_from('>I',raw,4)[0];body=bytearray(raw[8:8+n])
 if body[454:457]==b'\x57\0\0':return {}
 assert sha(raw)==EXPECTED,('AITeam.UpdateGame changed: audit before applying',sha(raw))
 assert body[454]==184
 assert c.ref(struct.unpack_from('>H',body,455)[0])=='GameObject.CrashLog.(Ljava/lang/String;)V'
 body[454:457]=b'\x57\0\0';a[1]=raw[:8]+body+raw[8+n:]
 return {'AITeam.class':c.emit()}
