# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import sys,pathlib,struct,zipfile,json,re
P=pathlib.Path(__file__).resolve().parents[2];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(P/'tools/python'))
ns={'__file__':str(P/'patch_steve_team.py')};exec((P/'patch_steve_team.py').read_text().split('backup=P/')[0],ns);C=ns['ClassFile']
z=zipfile.ZipFile(P/'PetSoccer-Meme-Test/code.pak')
for name in ['GameField','MeshObject','GameObject']:
 b=z.read(name+'.class');(O/(name+'.class')).write_bytes(b);c=C(b)
 print(name,'FIELDS',[(c.ref(f[1]),c.ref(f[2])) for f in c.fields]);print('METHODS',[(c.ref(m[1]),c.ref(m[2])) for m in c.methods if name=='GameField' or any(s in c.ref(m[1]).lower() for s in ['mesh','coll','position','scale','flag'])])
b=(P/'PetSoccer-Meme-Test/Data/Levels/Niedzwiedzie/Niedzwiedzie.map').read_bytes()
print('HEADER',b[:240].hex(' '))
for m in re.finditer(rb'[\x20-\x7e]{4,}',b):
 if any(x in m[0].lower() for x in [b'iglo',b'choink',b'field',b'football',b'zaspa',b'soccer',b'position']):print(m.start(),m[0], b[max(0,m.start()-30):m.end()+120].hex(' '))
