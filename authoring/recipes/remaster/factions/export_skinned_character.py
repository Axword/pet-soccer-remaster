"""0x101 two-influence skin export, validated against robot's 36-byte stream."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,struct,json
from mathutils import Matrix,Vector,Quaternion
P=pathlib.Path(__file__).parent
def export_skin(model,stem,output_root=None):
 source=(P/'build_steve.py').read_text();env={'__file__':str(P/'build_steve.py')}
 exec(source.split('bpy.ops.object.select_all')[0],env)
 exec('def track_values'+source.split('def track_values',1)[1].split('sample_frames=',1)[0],env)
 src,nodes,bind=env['src'],env['nodes'],env['world'];value,tracks=env['value'],env['tracks'];bones=model['bones'];vertices=model['vertices'];weights=model['weights'];faces=model['faces'];uv=model['uv'];normals=model['normals']
 frames=range(3141);positions=[[] for k in bones];bind_inv=[m.inverted() for m in bind]
 foot_refs=[]
 for n in nodes:
  if n['name'] in ('stopaP01_0','stopaP_0'):foot_refs.append((n['index'],[Vector(struct.unpack_from('<3f',src,n['pointers'][8]+j*12)) for j in range(n['counts'][0])]))
 baseline=min((bind[idx]@v).y for idx,vs in foot_refs for v in vs)
 pivots=[Vector(b['pivot']) for b in bones]
 footverts=[i for i,ww in enumerate(weights) if any(bones[k]['name'] in ['LFoot','RFoot'] and w>.15 for k,w in ww)]
 if not footverts:footverts=[i for i,v in enumerate(vertices) if v[1]<5]
 for frame in frames:
  ws=[]
  for n,ts in zip(nodes,tracks):
   v,q,s=value(ts[0],frame),value(ts[1],frame,True),value(ts[2],frame)
   m=Matrix.Translation(v)@Quaternion((q[3],-q[0],-q[1],-q[2])).to_matrix().to_4x4()@Matrix.Diagonal((*s,1))
   if n['parent']>=0:m=ws[n['parent']]@m
   ws.append(m)
  rotations=[(ws[b['native']].to_3x3()@bind_inv[b['native']].to_3x3()) for b in bones];targets=[]
  for k,b in enumerate(bones):
   par=b['parent'];targets.append(pivots[k]+ws[0].translation-bind[0].translation if par<0 else targets[par]+rotations[par]@(pivots[k]-pivots[par]))
  old_floor=min((ws[idx]@v).y for idx,vs in foot_refs for v in vs)-baseline
  new_floor=min(sum((targets[k]+rotations[k]@(Vector(vertices[i])-pivots[k])).y*w for k,w in weights[i]) for i in footverts)
  correction=old_floor-new_floor
  for k,b in enumerate(bones):
   target=targets[k]+Vector((0,correction,0));positions[k].append(tuple(ws[b['native']].inverted()@target))
 order=[]
 def visit(idx):
  order.append(('old',idx))
  for n in nodes:
   if n['parent']==idx:visit(n['index'])
  for k,b in enumerate(bones):
   if b['native']==idx:order.append(('bone',k))
 for n in nodes:
  if n['parent']==-1:visit(n['index'])
 order.append(('skin',0));indices={key:i for i,key in enumerate(order)};assert len(order)<256
 out=bytearray(src[:5344]);u=lambda b,o:struct.unpack_from('<I',b,o)[0];pack=lambda *v:struct.pack('<'+'I'*len(v),*v)
 struct.pack_into('<I',out,8,len(order));out[16:48]=(stem+'.png').encode().ljust(32,b'\0')
 struct.pack_into('<II',out,5268,sum(n['counts'][1] for n in nodes if n['type']==4)+len(faces),sum(n['counts'][0] for n in nodes if n['type']==4)+len(vertices))
 struct.pack_into('<6f',out,5280,*(min(v[k] for v in vertices) for k in range(3)),*(max(v[k] for v in vertices) for k in range(3)))
 for kind,k in order:
  base=len(out)
  if kind=='old':
   n=nodes[k];old=n['offset'];block=bytearray(src[old:old+n['size']])
   if n['type'] in (1,2):struct.pack_into('<I',block,0,3);block[36:80]=bytes(44);block[124:152]=bytes(28)
   for j in range(108,152,4):
    ptr=u(block,j)
    if ptr:struct.pack_into('<I',block,j,ptr-old+base)
   for j in (108,112,116):
    t=u(block,j)
    if t:
     local=t-base;struct.pack_into('<I',block,local+12,u(block,local+12)-old+base)
   parent=indices[('old',n['parent'])] if n['parent']>=0 else -1;children=n['children']+sum(b['native']==k for b in bones)
  else:
   block=bytearray(156);struct.pack_into('<I',block,0,4 if kind=='bone' else 2)
   block[4:36]=( ('CX_'+bones[k]['name']) if kind=='bone' else (stem+'_0')).encode()[:31].ljust(32,b'\0');children=0
   def stream(pointer,data):struct.pack_into('<I',block,pointer,base+len(block));block.extend(data)
   if kind=='bone':
    b=bones[k];parent=indices[('old',b['native'])];struct.pack_into('<I',block,76,2)
    t=base+len(block);stream(108,pack(0,3141,3,t+28)+struct.pack('<3f',*positions[k][0])+b''.join(pack(f)+struct.pack('<3f',*v) for f,v in zip(frames,positions[k])))
    r=bind_inv[b['native']].to_quaternion().normalized();rotation=(-r.x,-r.y,-r.z,r.w)
   else:
    parent=-1;nv,nf=len(vertices),len(faces);struct.pack_into('<11I',block,36,nv,nf,0,nf,0,0,0,nv,0,0,2)
    struct.pack_into('<6f',block,80,*(min(v[j] for v in vertices) for j in range(3)),*(max(v[j] for v in vertices) for j in range(3)))
    flat=[i for f in faces for i in f];stream(124,struct.pack('<'+'H'*len(flat),*flat));stream(128,bytes(nf*2));stream(132,struct.pack('<'+'H'*len(flat),*flat));stream(136,struct.pack('<'+'f'*(nv*2),*(c for a,b in uv for c in (a,1-b))));stream(140,struct.pack('<'+'f'*(nv*3),*(c for v in vertices for c in v)));stream(144,struct.pack('<'+'f'*(nv*3),*(c for v in normals for c in v)))
    blending=bytearray()
    for v,ww in zip(vertices,weights):
     a,w=ww[0];b,z=ww[1] if len(ww)>1 else (a,0.0);va=Vector(v)-pivots[a];vb=Vector(v)-pivots[b]
     blending.extend(struct.pack('<HH8f',indices[('bone',a)],indices[('bone',b)],*va,*vb,w,z))
    stream(148,blending);t=base+len(block);stream(108,pack(0,1,3,t+28)+struct.pack('<3f',0,0,0)+pack(0)+struct.pack('<3f',0,0,0));rotation=(0,0,0,1)
   for j,val in [(112,rotation),(116,(1,1,1))]:
    t=base+len(block);stream(j,pack(0,1,3,t+16+len(val)*4)+struct.pack('<'+'f'*len(val),*val)+pack(0)+struct.pack('<'+'f'*len(val),*val))
   struct.pack_into('<I',block,152,len(block))
  struct.pack_into('<hH',block,104,parent,children);out.extend(block)
 target=(pathlib.Path(output_root) if output_root else P/'Crossover-Pack')/'Data/Meshes/Animals';target.mkdir(parents=True,exist_ok=True);path=target/(stem+'.3da');path.write_bytes(out)
 from face_forward import turn_model
 turn_model(path,skip_skinned=True)
 (target/(stem+'.ini')).write_bytes((P/'robot-reference.ini').read_bytes())
 from inspect_3da import inspect
 result=inspect(path);assert result['end']==len(out);(P/(stem+'-skin-check.json')).write_text(json.dumps({'nodes':len(order),'bytes':len(out),'vertices':len(vertices),'faces':len(faces),'adapter_bones':len(bones)},indent=2))
 return path
