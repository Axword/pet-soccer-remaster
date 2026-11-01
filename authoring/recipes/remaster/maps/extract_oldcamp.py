# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,math,collections
O=pathlib.Path(__file__).parent;P=O.parents[1];sys.path.insert(0,str(P/'tools/python'))
from zenkit.world.world import World
from zenkit import Vfs,Texture
from PIL import Image
w=World.load(O/'source/world.zen');m=w.mesh;ps=[(v.x,v.y,v.z) for v in m.positions];fs=m.features
materials=m.materials;sel=[];stats=collections.Counter()
for p in m.polygons:
 ids=p.position_indices;coords=[ps[i] for i in ids];mx=sum(v[0] for v in coords)/len(coords);my=sum(v[1] for v in coords)/len(coords);mz=sum(v[2] for v in coords)/len(coords)
 if -6000<mx<3000 and -7000<mz<1500 and my>100 and my<8500 and not p.is_portal and materials[p.material_index].texture:
  sel.append((p.material_index,ids,p.feature_indices));stats[p.material_index]+=len(ids)-2
print('SEL',len(sel),'TOPMATERIALS',[(i,materials[i].name,materials[i].texture,n) for i,n in stats.most_common(36)],flush=True)
# Native 3da has 32 material slots; 30 selected exact source textures cover the backdrop.
texstats=collections.Counter()
for i,n in stats.items():texstats[materials[i].texture]+=n
keeptex={t for t,n in texstats.most_common(27)}
keep={i for i in stats if materials[i].texture in keeptex}
out={'positions':ps,'features':[{'uv':[f.texture.x,f.texture.y],'normal':[f.normal.x,f.normal.y,f.normal.z]} for f in fs], 'polygons':[(i,p,f) for i,p,f in sel if i in keep], 'materials':{i:materials[i].texture for i in keep}}
(O/'source/oldcamp-source.json').write_text(json.dumps(out,separators=(',',':')))
v=Vfs();v.mount_disk(pathlib.Path(str(_authoring_pathlib.Path(_authoring_os.environ['GOTHIC_GAME_DIR']) / 'Data/Textures.vdf')));items={}
def walk(n):
 for c in n.children:
  if c.is_dir():walk(c)
  else:items[c.name.upper()]=c
walk(v.root)
for i in keep:
 tex=materials[i].texture;name=tex.rsplit('.',1)[0].upper()+'-C.TEX';node=items.get(name)
 if not node:print('MISSING',name);continue
 path=O/'source'/name;path.write_bytes(node.data);t=Texture.load(path);im=Image.frombytes('RGBA',(t.width,t.height),t.mipmap_rgba(0));im.save(O/'source'/(name+'.png'))
print('DONE',flush=True)
