# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,struct,re,json
P=pathlib.Path(__file__).resolve().parents[2];b=(P/'PetSoccer-Meme-Test/Data/Levels/Niedzwiedzie/Niedzwiedzie.map').read_bytes();out=[]
for m in re.finditer(rb'\x17\x00.{4}\x0a\x00MeshObject|FieldCorner|FieldCenter|FieldGate|Terrain|SoccerModule',b,re.S):
 end=b.find(b'\x03\x00',m.end()+5)
 tag=b.find(b'\x04\x00\x40\x00\x00\x00',m.end(),m.end()+600)
 if tag<0:continue
 matrix=struct.unpack_from('<16f',b,tag+6)
 name='';match=re.search(rb'\x16\x00.{4}(.{2})([^\0\x01\x02\x03\x04\x05]+)',b[tag+70:tag+200],re.S)
 mesh=re.search(rb'[A-Za-z.:\\ ]+\.3[dD][aA]',b[m.end():tag])
 print(m.start(),m[0],mesh[0].decode() if mesh else '',matrix)
