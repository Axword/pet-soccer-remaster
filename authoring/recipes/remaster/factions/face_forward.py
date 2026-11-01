"""Rotate the entire native animation through 180 degrees about game Y."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,struct,sys
from inspect_3da import inspect
def turn_model(path,skip_skinned=False):
 path=pathlib.Path(path);b=bytearray(path.read_bytes());data=inspect(path)
 u=lambda o:struct.unpack_from('<I',b,o)[0]
 for n in data['nodes']:
  if n['parent']!=-1 or (skip_skinned and n['type']==2):continue
  pos,rot=n['pointers'][:2]
  if pos:
   count,kind,start=u(pos+4),u(pos+8),u(pos+12)
   size={1:60,2:40,3:16}[kind];offsets={1:(24,36,48),2:(4,16,28),3:(4,)}[kind]
   for i in range(count):
    for off in offsets:
     at=start+i*size+off;x,y,z=struct.unpack_from('<3f',b,at);struct.pack_into('<3f',b,at,-x,y,-z)
  if rot:
   count,kind,start=u(rot+4),u(rot+8),u(rot+12);assert kind==3
   for i in range(count):
    at=start+i*20+4;x,y,z,w=struct.unpack_from('<4f',b,at);struct.pack_into('<4f',b,at,z,-w,-x,y)
 stage=path.with_suffix('.facing-updated');stage.write_bytes(b);stage.replace(path)
 return len(b)
if __name__=='__main__':print(turn_model(sys.argv[1]))
