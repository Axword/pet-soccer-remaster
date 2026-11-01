# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json
O=pathlib.Path(__file__).parent;P=O.parents[1];sys.path.insert(0,str(P/'tools/python'))
from zenkit import Vfs
from zenkit.world.world import World
root=pathlib.Path(str(_authoring_pathlib.Path(_authoring_os.environ['GOTHIC_GAME_DIR']) / 'Data'));v=Vfs();v.mount_disk(root/'worlds.VDF');items=[]
def walk(n,path=''):
 for c in n.children:
  p=path+'/'+c.name
  if c.is_dir():walk(c,p)
  else:items.append((p,c))
walk(v.root);print('FILES',[(p,len(c.data)) for p,c in items],flush=True)
path,n=next((p,c) for p,c in items if p.upper().endswith('/WORLD.ZEN'));fn=O/'source/world.zen';fn.parent.mkdir(exist_ok=True);fn.write_bytes(n.data)
w=World.load(fn);m=w.mesh;print('WORLD',len(m.positions),len(m.polygons),len(m.materials),flush=True)
print('WAYNETAPI',dir(w.way_net),flush=True)
print('MATERIALS',[(i,x.name,x.texture) for i,x in enumerate(m.materials)],flush=True)
pts=w.way_net.points;print('POINTAPI',dir(pts[0]),flush=True)
waypoints=[{'name':p.name,'position':[p.position.x,p.position.y,p.position.z]} for p in pts]
(O/'source/waypoints.json').write_text(json.dumps(waypoints));print('WAYPOINTS',waypoints[:10],flush=True)
