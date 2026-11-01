"""Visible-skeleton animation repair; original football helpers/timing are retained.

Executed with Blender's mathutils. This does not change physics or Java state.
Gothic uses real owned G1 MAN clips. Witcher receives custom in-place animation.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,struct,json,math,bisect,hashlib,collections,os
from mathutils import Matrix,Vector,Quaternion
R=pathlib.Path(__file__).parent;P=R.parents[3];F=P/'remaster/factions';S=P/'Remaster-Pack';sys.path.insert(0,str(F))
from inspect_3da import inspect
FRAMES=range(3141)
GOTHIC=['bezimienny','diego','wrzod','cx_bezimienny','cx_diego','cx_gorn','cx_milten','cx_lester','cx_xardas','cx_thorus']
WITCHER=['geralt']+['cx_w3_'+s for s in ['geralt','ciri','yennefer','triss','keira','avallach','zoltan']]
JOINTS=['BIP01','BIP01 PELVIS','BIP01 SPINE2','BIP01 NECK','BIP01 HEAD','BIP01 L CLAVICLE','BIP01 L UPPERARM','BIP01 L FOREARM','BIP01 L HAND','BIP01 R CLAVICLE','BIP01 R UPPERARM','BIP01 R FOREARM','BIP01 R HAND','BIP01 L THIGH','BIP01 L CALF','BIP01 L FOOT','BIP01 R THIGH','BIP01 R CALF','BIP01 R FOOT']
LABELS=['Root','Pelvis','Spine','Neck','Head','LClav','LArm','LFore','LHand','RClav','RArm','RFore','RHand','LThigh','LCalf','LFoot','RThigh','RCalf','RFoot']
PARENTS=[-1,0,1,2,3,2,5,6,7,2,9,10,11,1,13,14,1,16,17]
gsrc=json.loads((P/'source-assets/gothic/source-model.json').read_text());grest=[]
for j in gsrc['joints']:
 m=Matrix(j['matrix']);grest.append(grest[j['parent']]@m if j['parent']>=0 else Matrix.Translation(gsrc['root_translation'])@m)
gindices=[next(i for i,j in enumerate(gsrc['joints']) if j['name']==label) for label in JOINTS]
clips={name:json.loads((R/(name+'.json')).read_text()) for name in ['HUMANS-S_RUN.MAN','HUMANS-S_RUNL.MAN','HUMANS-S_WALK.MAN','HUMANS-S_WALKL.MAN']}

def gs_pose(name,phase):
 a=clips[name];at=(phase%1)*a['frames'];i=int(at);j=(i+1)%a['frames'];fac=at-i;world=[]
 for idx,bone in enumerate(gsrc['joints']):
  if idx in a['indices']:
   k=a['indices'].index(idx);v=a['samples'][i*a['nodes']+k];w=a['samples'][j*a['nodes']+k]
   # Native ZenKit ABI returns xyzw; the Python Quat wrapper incorrectly names
   # the first C float w. Reconstruct the measured original xyzw and invert
   # Max/Gothic's passive rotation. Confirmed against original bind skeleton.
   def quat(s):x,y,z,w=s['q'];return Quaternion((z,w,x,y)).inverted().normalized()
   q=quat(v).slerp(quat(w),fac);pos=Vector(v['p']).lerp(Vector(w['p']),fac)
   m=Matrix.Translation(pos)@q.to_matrix().to_4x4()
  else:m=Matrix(bone['matrix'])
  world.append(world[bone['parent']]@m if bone['parent']>=0 else m)
 return world

def track(b,t,dim,default):
 if not t:return [0],[default]
 cnt,kind,start=struct.unpack_from('<III',b,t+4);stride={1:4+20+dim*12,2:4+dim*12,3:4+dim*4}[kind]
 fs=[];vs=[]
 for i in range(cnt):
  o=start+i*stride;fs.append(struct.unpack_from('<I',b,o)[0]);vs.append(struct.unpack_from('<'+'f'*dim,b,o+4+(20 if kind==1 else 0)))
 return fs,vs
def sample(t,f,dim):
 fs,vs=t;i=max(0,bisect.bisect_right(fs,f)-1)
 if i==len(fs)-1:return vs[i]
 a,b=vs[i],vs[i+1];q=(f-fs[i])/(fs[i+1]-fs[i])
 if dim==4:
  x=Quaternion((a[3],-a[0],-a[1],-a[2])).slerp(Quaternion((b[3],-b[0],-b[1],-b[2])),q);return(-x.x,-x.y,-x.z,x.w)
 return tuple(x+(y-x)*q for x,y in zip(a,b))
def native_world(nodes,b,f,tracks):
 world=[]
 for n,t in zip(nodes,tracks):
  p,q,s=[sample(tt,f,dim) for tt,dim in zip(t,[3,4,3])];m=Matrix.Translation(p)@Quaternion((q[3],-q[0],-q[1],-q[2])).to_matrix().to_4x4()@Matrix.Diagonal((*s,1));world.append(world[n['parent']]@m if n['parent']>=0 else m)
 return world
def region(f):
 for lo,hi,kind in [(0,30,'idle'),(35,105,'look'),(110,140,'walk'),(195,225,'back'),(230,260,'backrun'),(265,285,'run'),(1865,2285,'audience')]:
  if lo<=f<=hi:return kind,(f-lo)/(hi-lo)
 return None,0
def rx(x):return Matrix.Rotation(x,3,'X')
def ry(x):return Matrix.Rotation(x,3,'Y')
def rz(x):return Matrix.Rotation(x,3,'Z')
def custom_witcher(piv,bind_rot,kind,phase,stem):
 cycle=phase*2*math.pi
 if kind=='audience':cycle*=7
 move=kind in ['walk','run','back','backrun'];run=kind in ['run','backrun'];amp=.66 if run else .33
 D=[Matrix.Identity(3) for _ in LABELS]
 sway=math.sin(cycle)*(.012 if move else .018);D[1]=ry(sway);D[2]=ry(-sway*.4)@rx(.06 if run else .012+math.sin(cycle)*.008);D[3]=D[2];D[4]=D[2]@ry((math.sin(cycle)*.10 if kind=='look' else .02*math.sin(cycle)))
 for side,clav,arm,fore,hand,thigh,calf,foot in [(1,5,6,7,8,13,14,15),(-1,9,10,11,12,16,17,18)]:
  # Aim anatomical bind segments at a relaxed, slightly flexed rest. This also
  # handles the older procedural Geralt whose arms already point down.
  original=(piv[fore]-piv[arm]).normalized();desired=Vector((side*.12,-1,.055)).normalized();lower=original.rotation_difference(desired).to_matrix()
  swing=math.sin(cycle+(0 if side>0 else math.pi))*(amp*.65 if move else .025)
  D[clav]=D[2];D[arm]=D[2]@rx(-swing)@lower
  orig_fore=(piv[hand]-piv[fore]).normalized();desired_fore=Vector((side*.04,-1,.17 if not move else .40)).normalized();D[fore]=D[2]@rx(-swing)@orig_fore.rotation_difference(desired_fore).to_matrix();D[hand]=D[fore]
  leg=math.sin(cycle+(0 if side>0 else math.pi))*amp*( -1 if kind in ['back','backrun'] else 1) if move else 0
  D[thigh]=D[1]@rx(leg);D[calf]=D[1]@rx(leg-max(0,-math.sin(cycle+(0 if side>0 else math.pi)))*amp*1.25);D[foot]=D[1]@rx(leg*.22)
 roots=[];rots=[]
 lift=(.18*math.cos(cycle*2) if move else .12*math.sin(cycle))
 for k in range(len(LABELS)):
  par=PARENTS[k];roots.append(piv[k]+Vector((0,lift,0)) if par<0 else roots[par]+D[par]@(piv[k]-piv[par]));rots.append(D[k]@bind_rot[k])
 return roots,rots

def reduce_keys(values,dim,tolerance,forced):
 keep=set(forced)|{0,len(values)-1};segments=sorted(keep)
 def error(a,b,i):
  t=(i-a)/(b-a)
  if dim==4:
   qa=Quaternion(values[a]);qb=Quaternion(values[b]);qi=qa.slerp(qb,t);return qi.rotation_difference(Quaternion(values[i])).angle
  return (Vector(values[a]).lerp(Vector(values[b]),t)-Vector(values[i])).length
 def rec(a,b):
  if b-a<2:return
  best=0;idx=-1
  for i in range(a+1,b):
   e=error(a,b,i)
   if e>best:best=e;idx=i
  if best>tolerance:keep.add(idx);rec(a,idx);rec(idx,b)
 for a,b in zip(segments,segments[1:]):rec(a,b)
 return sorted(keep)
def emit_track(block,base,ptr,values,dim,quats=False):
 forced={0,30,31,34,35,105,106,109,110,140,141,194,195,225,226,229,230,260,261,264,265,285,286,1864,1865,2285,2286,3140}
 selected=reduce_keys(values,dim,.001 if dim==4 else .012,forced)
 # Quaternion values here are active wxyz; 3DA stores inverse xyzw.
 def val(v):return (-v[1],-v[2],-v[3],v[0]) if quats else v
 pos=base+len(block);struct.pack_into('<I',block,ptr,pos);cached=val(values[0]);keypos=pos+16+dim*4;block.extend(struct.pack('<4I',0,len(selected),3,keypos));block.extend(struct.pack('<'+'f'*dim,*cached))
 for f in selected:block.extend(struct.pack('<I'+'f'*dim,f,*val(values[f])))
 return len(selected)

def process(stem,gothic):
 src=S/'Data/Meshes/Animals'/(stem+'.3da');raw=src.read_bytes();meta=inspect(src);nodes=meta['nodes'];tracks=[[track(raw,t,dim,default) for t,dim,default in zip(n['pointers'][:3],[3,4,3],[(0,0,0),(0,0,0,1),(1,1,1)])] for n in nodes]
 selected=[next(n['index'] for n in nodes if n['name']=='CX_'+label) for label in LABELS];cx=set(selected);w0=native_world(nodes,raw,0,tracks);piv=[w0[i].translation.copy() for i in selected];bind_rot=[w0[i].to_3x3().normalized() for i in selected]
 frames_pos=[[] for _ in selected];frames_q=[[] for _ in selected];ground=[];changes=collections.Counter()
 # Actual static bind orientation is measured per output; this accommodates
 # older custom copies and current 2x models without regeneration/scaling.
 gfactor=(piv[4]-piv[15]).length/(grest[gindices[4]].translation-grest[gindices[15]].translation).length if gothic else 1
 g_align=Matrix.Identity(3)
 # Source and deployed native forward are both +Z after the two authored180°
 # transforms; use skeleton axes measured from L/R hips and head/feet.
 if gothic:
  sx=(grest[gindices[13]].translation-grest[gindices[16]].translation).normalized();nx=(piv[13]-piv[16]).normalized();g_align=sx.rotation_difference(nx).to_matrix()
 feet=[]
 skin=next(n for n in nodes if n['type']==2)
 for vi in range(skin['counts'][0]):
  at=skin['pointers'][10]+vi*36;a,b,*v=struct.unpack_from('<HH8f',raw,at)
  if (a in [selected[15],selected[18]] and v[6]>.3) or (b in [selected[15],selected[18]] and v[7]>.3):feet.append((a,b,v))
 baseline=min(((w0[a]@Vector(v[:3]))*v[6]+(w0[b]@Vector(v[3:6]))*v[7]).y for a,b,v in feet)
 max_head_turn=0
 for f in FRAMES:
  old=native_world(nodes,raw,f,tracks);root=old[0];kind,phase=region(f);roots=[old[i].translation.copy() for i in selected];rots=[old[i].to_3x3().normalized() for i in selected]
  if kind:
   if gothic:
    clip='HUMANS-S_RUNL.MAN' if kind in ['run','backrun'] else 'HUMANS-S_WALKL.MAN' if kind in ['walk','back'] else 'HUMANS-S_WALK.MAN' if kind=='look' else 'HUMANS-S_RUN.MAN'
    if kind=='audience':phase=(phase*7)%1
    if kind in ['back','backrun']:phase=1-phase
    gw=gs_pose(clip,phase)
    for k,j in enumerate(gindices):
     delta=g_align@(gw[j].to_3x3()@grest[j].to_3x3().inverted())@g_align.inverted();rots[k]=delta@bind_rot[k]
     relative=gw[j].translation-gw[0].translation;reference=grest[j].translation-grest[0].translation
     roots[k]=piv[k]+g_align@(relative-reference)*gfactor
    # The exported game skin deliberately merges the two lower source spine
    # bones into Pelvis. Preserve its connected reduced19-bone proportions:
    # driving independent source translations here would split the waist.
    connected=[]
    for k in range(len(LABELS)):
     par=PARENTS[k];connected.append(piv[k].copy() if par<0 else connected[par]+(rots[par]@bind_rot[par].inverted())@(piv[k]-piv[par]))
    roots=connected
    if kind=='look':
     # Source's relaxed walk-ready idle plus a restrained smooth eye-line scan.
     rots[4]=ry(math.sin(phase*2*math.pi)*.16)@rots[4]
   else:roots,rots=custom_witcher(piv,bind_rot,kind,phase,stem)
   changes[kind]+=1
  else:
   # Keep football actions, but bound the robot's independent360° head helper
   # to a human neck and connect the head pivot to the authored neck chain.
   rel=(rots[3].inverted()@rots[4]).to_quaternion()
   if rel.w<0:rel.negate()
   angle=rel.angle
   if angle>math.radians(65):rots[4]=rots[3]@Quaternion((1,0,0,0)).slerp(rel,math.radians(65)/angle).to_matrix();changes['head_clamped']+=1
   roots[4]=roots[3]+(rots[3]@bind_rot[3].inverted())@(piv[4]-piv[3])
  # Cosmetic floor correction. Root/ball helpers are never edited. In ordinary
  # idle/walk/run preserve the deployed standing baseline without root motion.
  if kind:
   matrices={idx:Matrix.Translation(p)@r.to_4x4() for idx,p,r in zip(selected,roots,rots)}
   low=min(((matrices[a]@Vector(v[:3]))*v[6]+(matrices[b]@Vector(v[3:6]))*v[7]).y for a,b,v in feet)
   fix=baseline-low
   roots=[v+Vector((0,fix,0)) for v in roots]
  inverse=root.inverted()
  for k,(pos,rot) in enumerate(zip(roots,rots)):
   local=inverse@(Matrix.Translation(pos)@rot.to_4x4());q=local.to_quaternion().normalized()
   if frames_q[k] and q.dot(Quaternion(frames_q[k][-1]))<0:q.negate()
   frames_pos[k].append(tuple(local.translation));frames_q[k].append(tuple(q))
 out=bytearray(raw[:5344]);stats=[]
 for n in nodes:
  base=len(out);oldoff=n['offset']
  if n['index'] in cx:
   k=selected.index(n['index']);block=bytearray(raw[oldoff:oldoff+156]);struct.pack_into('<hH',block,104,0,0);block[108:152]=bytes(44)
   countp=emit_track(block,base,108,frames_pos[k],3);countq=emit_track(block,base,112,frames_q[k],4,True)
   t=base+len(block);struct.pack_into('<I',block,116,t);block.extend(struct.pack('<4I3fI3f',0,1,3,t+28,1,1,1,0,1,1,1));struct.pack_into('<I',block,152,len(block));stats.append(dict(bone=n['name'],pos_keys=countp,rot_keys=countq))
  else:
   block=bytearray(raw[oldoff:oldoff+n['size']]);children=n['children']-sum(nodes[i]['parent']==n['index'] for i in selected)+(len(selected) if n['index']==0 else 0);struct.pack_into('<H',block,106,children)
   for j in range(108,152,4):
    ptr=struct.unpack_from('<I',block,j)[0]
    if ptr:struct.pack_into('<I',block,j,ptr-oldoff+base)
   for j in [108,112,116]:
    ptr=struct.unpack_from('<I',block,j)[0]
    if ptr:
     local=ptr-base;key=struct.unpack_from('<I',block,local+12)[0];struct.pack_into('<I',block,local+12,key-oldoff+base)
  out.extend(block)
 target=R/'Pack/Data/Meshes/Animals'/(stem+'.3da');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(out);check=inspect(target);assert check['end']==len(out) and check['count']==meta['count'] and check['frames']==meta['frames']
 report=dict(stem=stem,family='Gothic' if gothic else 'Witcher',source=str(src),source_sha256=hashlib.sha256(raw).hexdigest(),output=str(target),sha256=hashlib.sha256(out).hexdigest(),source_bytes=len(raw),bytes=len(out),changes=dict(changes),tracks=stats,collision_or_Java_changes=False,root_motion='In place; original football helper rig and durations remain unchanged',source_clips=list(clips) if gothic else [],source_gothic_scale=gfactor)
 print('REPAIRED',stem,len(raw),'->',len(out),dict(changes),flush=True);return report

if __name__=='__main__':
 targets=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else GOTHIC+WITCHER
 reports=[process(stem,stem in GOTHIC) for stem in targets];manifest=R/('manifest-'+('-'.join(targets) if len(targets)<3 else 'all')+'.json')
 old=json.loads(manifest.read_text()) if manifest.exists() else [];byname={r['stem']:r for r in old};byname.update({r['stem']:r for r in reports});manifest.write_text(json.dumps(list(byname.values()),indent=2))
