"""Reuse the verified old-engine writer for six arbitrary geometry groups."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib
P=pathlib.Path(__file__).parent
def export_character(parts,stem):
 source=(P/'build_steve.py').read_text()
 env={'__file__':str(P/'build_steve.py')}
 exec(source.split('bpy.ops.object.select_all')[0],env)
 from mathutils import Vector
 for p in parts:p['pivot']=Vector(p['pivot'])
 block='def track_values'+source.split('def track_values',1)[1].split('# Render views',1)[0]
 replacements={
  "out[16:48]=b'steve.png'.ljust(32,b'\\0')":f"out[16:48]=b'{stem}.png'.ljust(32,b'\\0')",
  'bone_faces+72,bone_vertices+144':"bone_faces+sum(len(p['faces']) for p in parts),bone_vertices+sum(len(p['vertices']) for p in parts)",
  "struct.pack_into('<6f',out,5280,-8*VOXEL,0,-4*VOXEL,8*VOXEL,32*VOXEL,4*VOXEL)":"struct.pack_into('<6f',out,5280,*(min(v[k] for p in parts for v in p['vertices']) for k in range(3)),*(max(v[k] for p in parts for v in p['vertices']) for k in range(3)))",
  "struct.pack_into('<11I',block,36,24,12,0,12,0,0,0,24,0,0,2)":"nv=len(p['vertices']);nf=len(p['faces']);struct.pack_into('<11I',block,36,nv,nf,0,nf,0,0,0,nv,0,0,2)",
  "struct.pack('<36H',*flatfaces)":"struct.pack('<'+'H'*len(flatfaces),*flatfaces)",
  'stream(128,bytes(24))':'stream(128,bytes(nf*2))',
  "struct.pack('<48f',*(v for xy in native_uv for v in xy))":"struct.pack('<'+'f'*(nv*2),*(v for xy in native_uv for v in xy))",
  "struct.pack('<72f',*(v for xyz in verts for v in xyz))":"struct.pack('<'+'f'*(nv*3),*(v for xyz in verts for v in xyz))",
  "struct.pack('<72f',*(v for xyz in norms for v in xyz))":"struct.pack('<'+'f'*(nv*3),*(v for xyz in norms for v in xyz))",
  "target=P/'PetSoccer-Steve-Test'/'Data'/'Meshes'/'Animals'":"target=P/'Crossover-Pack'/'Data'/'Meshes'/'Animals';target.mkdir(parents=True,exist_ok=True)",
  "target/'steve.3da'":f"target/'{stem}.3da'",
  "target/'steve.3da.updated'":f"target/'{stem}.3da.updated'",
  "target/'steve.ini'":f"target/'{stem}.ini'",
  "(target/'robocik.ini').read_bytes()":"(P/'PetSoccer-Steve-Test/Data/Meshes/Animals/robocik.ini').read_bytes()",
  "P/'steve-export-check.json'":f"P/'{stem}-export-check.json'",
 }
 for a,b in replacements.items():
  assert a in block,a;block=block.replace(a,b)
 env['parts']=parts
 exec(block,env)
 return env['target']/(stem+'.3da')
