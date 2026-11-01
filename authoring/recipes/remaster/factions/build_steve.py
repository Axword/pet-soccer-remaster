"""Steve authoring mesh and experimental Chrome Engine 0x101 writer.
Only writes inside the isolated test copy. Does not replace any original team.
Run using Blender --background --python build_steve.py.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import bpy,struct,json,pathlib,math,sys,bisect
from mathutils import Matrix,Vector,Quaternion
P=pathlib.Path(__file__).parent
sys.path.insert(0,str(P))
from inspect_3da import inspect
src=(P/'robot-reference.3da').read_bytes(); parsed=inspect(P/'robot-reference.3da')
u=lambda b,o:struct.unpack_from('<I',b,o)[0]
pack=lambda *v:struct.pack('<'+'I'*len(v),*v)
nodes=parsed['nodes']
VOXEL=1.75
def first_trs(n):
 vals=[]
 for i,t in enumerate(n['pointers'][:3]):
  if not t:vals.append((0,0,0) if i==0 else ((0,0,0,1) if i==1 else (1,1,1)));continue
  key=u(src,t+12);typ=u(src,t+8)
  off=key+4+(20 if typ==1 else 0)
  vals.append(struct.unpack_from('<'+'f'*(4 if i==1 else 3),src,off))
 p,q,s=vals
 # Max/Chrome quaternions store the inverse of Blender's active rotation.
 rot=Quaternion((q[3],-q[0],-q[1],-q[2])).to_matrix().to_4x4()
 return Matrix.Translation(p)@rot@Matrix.Diagonal((*s,1))
world=[]
for n in nodes:
 m=first_trs(n)
 world.append(world[n['parent']]@m if n['parent']>=0 else m)

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
col=bpy.data.collections.new('COL_Steve');bpy.context.scene.collection.children.link(col)
im=bpy.data.images.load(str(P/'steve.png'));im.pack()
mat=bpy.data.materials.new('MAT_Steve');mat.use_nodes=True
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest'
bs=mat.node_tree.nodes.get('Principled BSDF');mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=1
parts=[]
def box(name,lo,hi,uv,bone):
 x0,y0,z0=[v*VOXEL for v in lo];x1,y1,z1=[v*VOXEL for v in hi]
 a,b=uv;w=hi[0]-lo[0];h=hi[1]-lo[1];d=hi[2]-lo[2]
 faces=[
  ([(x0,y1,z0),(x1,y1,z0),(x1,y0,z0),(x0,y0,z0)],(a+d,b+d,w,h)),
  ([(x1,y1,z1),(x0,y1,z1),(x0,y0,z1),(x1,y0,z1)],(a+2*d+w,b+d,w,h)),
  ([(x0,y1,z1),(x0,y1,z0),(x0,y0,z0),(x0,y0,z1)],(a,b+d,d,h)),
  ([(x1,y1,z0),(x1,y1,z1),(x1,y0,z1),(x1,y0,z0)],(a+d+w,b+d,d,h)),
  ([(x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0)],(a+d,b,w,d)),
  ([(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],(a+d+w,b,w,d))]
 verts=[];uvs=[];tris=[];normals=[]
 for v,r in faces:
  k=len(verts);verts.extend(v);xx,yy,ww,hh=r
  uvs.extend([(xx/64,1-yy/64),((xx+ww)/64,1-yy/64),((xx+ww)/64,1-(yy+hh)/64),(xx/64,1-(yy+hh)/64)])
  tris.extend([(k,k+1,k+2),(k,k+2,k+3)])
  normal=(Vector(v[1])-Vector(v[0])).cross(Vector(v[2])-Vector(v[0])).normalized();normals.extend([tuple(normal)]*4)
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-z,y) for x,y,z in verts],[],tris);mesh.materials.append(mat)
 layer=mesh.uv_layers.new()
 for poly in mesh.polygons:
  for li in poly.loop_indices:layer.data[li].uv=uvs[mesh.loops[li].vertex_index]
 ob=bpy.data.objects.new(name,mesh);col.objects.link(ob)
 parts.append(dict(name=name,vertices=verts,uv=uvs,faces=tris,normals=normals,bone=bone))
box('Steve_Head',(-4,24,-4),(4,32,4),(0,0),43)
box('Steve_Body',(-4,12,-2),(4,24,2),(16,16),3)
box('Steve_RightArm',(-8,12,-2),(-4,24,2),(40,16),75)
box('Steve_LeftArm',(4,12,-2),(8,24,2),(32,48),54)
box('Steve_RightLeg',(-4,0,-2),(0,12,2),(0,16),22)
box('Steve_LeftLeg',(0,0,-2),(4,12,2),(16,48),4)
(P/'steve-mesh.json').write_text(json.dumps(parts),encoding='utf8')

# Keep Minecraft joints connected while inheriting the game's existing motion.
# The robot's shoulder/hip pivots differ from Steve's proportions, so simply
# attaching world-space cubes leaves limbs floating when a bone rotates.
pivots=[(0,24,0),(0,12,0),(-6,24,0),(6,24,0),(-2,12,0),(2,12,0)]
for p,v in zip(parts,pivots):p['pivot']=Vector(v)*VOXEL
def track_values(t,dim,default):
 if not t:return ([0],[default])
 count,typ,offset=u(src,t+4),u(src,t+8),u(src,t+12)
 size={1:4+20+dim*12,2:4+dim*12,3:4+dim*4}[typ]
 fs=[];vs=[]
 for j in range(count):
  k=offset+j*size;fs.append(u(src,k));o=k+4+(20 if typ==1 else 0)
  vs.append(struct.unpack_from('<'+'f'*dim,src,o))
 return fs,vs
tracks=[]
for n in nodes:
 tracks.append([track_values(t,d,default) for t,d,default in zip(n['pointers'][:3],[3,4,3],[(0,0,0),(0,0,0,1),(1,1,1)])])
def value(track,frame,quat=False):
 fs,vs=track;i=max(0,bisect.bisect_right(fs,frame)-1)
 if i+1==len(fs):return vs[i]
 f=(frame-fs[i])/(fs[i+1]-fs[i]);a=vs[i];b=vs[i+1]
 if quat:
  q=Quaternion((a[3],*a[:3])).slerp(Quaternion((b[3],*b[:3])),f);return(q.x,q.y,q.z,q.w)
 return tuple(x+(y-x)*f for x,y in zip(a,b))
sample_frames=list(range(0,3141))
position_keys=[[] for p in parts]
bind_inv=[m.inverted() for m in world]
original_feet=[]
for n in nodes:
 if n['name'] in ('stopaP01_0','stopaP_0'):
  original_feet.append((n['index'],[Vector(struct.unpack_from('<3f',src,n['pointers'][8]+j*12)) for j in range(n['counts'][0])]))
foot_bind=min((world[idx]@v).y for idx,vs in original_feet for v in vs)
for frame in sample_frames:
 ws=[]
 for n,ts in zip(nodes,tracks):
  v,q,s=value(ts[0],frame),value(ts[1],frame,True),value(ts[2],frame)
  m=Matrix.Translation(v)@Quaternion((q[3],-q[0],-q[1],-q[2])).to_matrix().to_4x4()@Matrix.Diagonal((*s,1))
  if n['parent']>=0:m=ws[n['parent']]@m
  ws.append(m)
 body=ws[3]@bind_inv[3]@Matrix.Translation(parts[1]['pivot'])
 targets=[body@(p['pivot']-parts[1]['pivot']) for p in parts]
 # Preserve the original motion's floor contact and jump height. Steve's rigid
 # legs do not share the robot's knee bend, so they need a small root correction.
 floor_old=min((ws[idx]@v).y for idx,vs in original_feet for v in vs)-foot_bind
 floor_new=min((targets[j]+(ws[parts[j]['bone']].to_3x3()@bind_inv[parts[j]['bone']].to_3x3())@(Vector(v)-parts[j]['pivot'])).y for j in (4,5) for v in parts[j]['vertices'])
 height_correction=floor_old-floor_new
 for j,p in enumerate(parts):
  target=targets[j];target.y+=height_correction
  position_keys[j].append(tuple(ws[p['bone']].inverted()@target))

# Preserve the original animation/helper tree, replacing visible geometry with
# named helpers. New Steve geometry is added as children of animation bones.
order=[]
def visit(i):
 order.append(('old',i))
 for n in nodes:
  if n['parent']==i:visit(n['index'])
 for j,p in enumerate(parts):
  if p['bone']==i:order.append(('new',j))
for n in nodes:
 if n['parent']==-1:visit(n['index'])
index={key:i for i,key in enumerate(order)}
out=bytearray(src[:5344]);struct.pack_into('<I',out,8,len(order))
out[16:48]=b'steve.png'.ljust(32,b'\0')
bone_vertices=sum(n['counts'][0] for n in nodes if n['type']==4)
bone_faces=sum(n['counts'][1] for n in nodes if n['type']==4)
struct.pack_into('<II',out,5268,bone_faces+72,bone_vertices+144)
struct.pack_into('<6f',out,5280,-8*VOXEL,0,-4*VOXEL,8*VOXEL,32*VOXEL,4*VOXEL)
for typ,i in order:
 base=len(out)
 if typ=='old':
  n=nodes[i];old=n['offset'];block=bytearray(src[old:old+n['size']])
  if n['type'] in (1,2):
   struct.pack_into('<I',block,0,3);block[36:80]=bytes(44)
   block[124:152]=bytes(28)
  for j in range(108,152,4):
   ptr=u(block,j)
   if ptr:struct.pack_into('<I',block,j,ptr-old+base)
  for j in (108,112,116):
   t=u(block,j)
   if t:
    local=t-base;key=u(block,local+12)
    struct.pack_into('<I',block,local+12,key-old+base)
  parent=index[('old',n['parent'])] if n['parent']>=0 else -1
  children=sum(x['parent']==i for x in nodes)+sum(x['bone']==i for x in parts)
 else:
  p=parts[i];parent=index[('old',p['bone'])];children=0;block=bytearray(156)
  struct.pack_into('<I',block,0,1);block[4:36]=(p['name']+'_0').encode().ljust(32,b'\0')
  struct.pack_into('<11I',block,36,24,12,0,12,0,0,0,24,0,0,2)
  verts=[tuple(Vector(v)-p['pivot']) for v in p['vertices']]
  norms=p['normals']
  struct.pack_into('<6f',block,80,*(min(v[k] for v in verts) for k in range(3)),*(max(v[k] for v in verts) for k in range(3)))
  def stream(ptr,data):
   struct.pack_into('<I',block,ptr,base+len(block));block.extend(data)
  flatfaces=[v for f in p['faces'] for v in f]
  stream(124,struct.pack('<36H',*flatfaces));stream(128,bytes(24))
  stream(132,struct.pack('<36H',*flatfaces))
  # Pet Soccer stores V from the TOP of the texture; Blender uses the bottom.
  native_uv=[(x,1-y) for x,y in p['uv']]
  stream(136,struct.pack('<48f',*(v for xy in native_uv for v in xy)))
  stream(140,struct.pack('<72f',*(v for xyz in verts for v in xyz)))
  stream(144,struct.pack('<72f',*(v for xyz in norms for v in xyz)))
  t=base+len(block);header=28
  stream(108,pack(0,len(sample_frames),3,t+header)+struct.pack('<3f',*position_keys[i][0])+b''.join(pack(f)+struct.pack('<3f',*v) for f,v in zip(sample_frames,position_keys[i])))
  rotation=bind_inv[p['bone']].to_quaternion().normalized()
  rotation=( -rotation.x,-rotation.y,-rotation.z,rotation.w )
  for j,val in [(112,rotation),(116,(1.,1.,1.))]:
   t=base+len(block);header=16+4*len(val)
   stream(j,pack(0,1,3,t+header)+struct.pack('<'+'f'*len(val),*val)+pack(0)+struct.pack('<'+'f'*len(val),*val))
  struct.pack_into('<I',block,152,len(block))
 struct.pack_into('<hH',block,104,parent,children);out.extend(block)
target=P/'PetSoccer-Steve-Test'/'Data'/'Meshes'/'Animals'
staged=target/'steve.3da.updated';staged.write_bytes(out);staged.replace(target/'steve.3da')
from face_forward import turn_model
turn_model(target/'steve.3da')
(target/'steve.ini').write_bytes((target/'robocik.ini').read_bytes())
result=inspect(target/'steve.3da');assert result['end']==len(out) and result['count']==126
assert u(out,5268)==sum(n['counts'][1] for n in result['nodes'])
assert u(out,5272)==sum(n['counts'][0] for n in result['nodes'])
(P/'steve-export-check.json').write_text(json.dumps({k:v for k,v in result.items() if k!='nodes'},indent=2))

# Render views of the authored mesh, explicitly separate from game validation.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.world.color=(.4,.4,.4);scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
for loc,energy,size in [((25,-40,65),90000,35),((-25,15,45),60000,30)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,0,24))-l.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(65,100,58));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,24))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=60;scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Steve.blend'))
for name,loc in [('front',(0,100,24)),('side',(100,0,24)),('preview',(65,100,58))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,24))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(P/('Steve-'+name+'.png'));bpy.ops.render.render(write_still=True)
print('STEVE_EXPORT_OK',len(out),'bytes; originals preserved')
