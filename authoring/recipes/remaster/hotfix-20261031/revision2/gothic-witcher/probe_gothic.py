# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json
R=pathlib.Path(__file__).parent; P=R.parents[3]; sys.path.insert(0,str(P/'tools/python'))
from zenkit import Vfs,ModelAnimation
v=Vfs(); v.mount_disk(pathlib.Path(str(_authoring_pathlib.Path(_authoring_os.environ['GOTHIC_GAME_DIR']) / 'Data/anims.VDF')))
index={}
def walk(n):
 for c in n.children:
  if c.is_dir():walk(c)
  else:index[c.name.upper()]=c
walk(v.root)
names=[n for n in index if n.startswith('HUMANS-') and any(s in n for s in ['S_RUN','S_WALK','S_FISTRUN','S_FISTWALK','S_1HRUN','S_1HWALK']) and n.endswith('.MAN')]
print('\n'.join(names)); (R/'animation-index.json').write_text(json.dumps(names,indent=2))
for n in ['HUMANS-S_RUN.MAN','HUMANS-S_RUNL.MAN','HUMANS-S_WALK.MAN','HUMANS-S_WALKL.MAN']:
 if n not in index:continue
 path=R/n;path.write_bytes(index[n].data);a=ModelAnimation.load(path)
 print(n,'frames',a.frame_count,'nodes',a.node_count,'fps',a.fps,'indices',a.node_indices)
 data=dict(name=a.name,frames=a.frame_count,nodes=a.node_count,fps=a.fps,indices=a.node_indices,samples=[dict(p=[s.position.x,s.position.y,s.position.z],q=[s.rotation.x,s.rotation.y,s.rotation.z,s.rotation.w]) for s in a.samples]);(R/(n+'.json')).write_text(json.dumps(data))
