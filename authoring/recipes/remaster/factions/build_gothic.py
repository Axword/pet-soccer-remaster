# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,math,collections
from mathutils import Matrix,Vector
P=pathlib.Path(__file__).parent;sys.path.insert(0,str(P.parent.parent/'tools/python'));sys.path.insert(0,str(P))
from zenkit import Vfs,ModelMesh,MorphMesh,Texture
from PIL import Image
from export_skinned_character import export_skin
D=P/'source-assets/gothic';v=Vfs()
for n in ['meshes.VDF','anims.VDF','Textures.vdf']:v.mount_disk(pathlib.Path(str(_authoring_pathlib.Path(_authoring_os.environ['GOTHIC_GAME_DIR']) / 'Data'))/n)
index={}
def walk(n):
 for c in n.children:
  if c.is_dir():walk(c)
  else:index[c.name.upper()]=c
walk(v.root)
def asset(name):
 path=D/name
 if not path.exists():path.write_bytes(index[name.upper()].data)
 return path
source=json.loads((D/'source-model.json').read_text());joints=source['joints'];world=[]
for j in joints:
 mat=Matrix(j['matrix']);mat=world[j['parent']]@mat if j['parent']>=0 else Matrix.Translation(source['root_translation'])@mat;world.append(mat)
defs=[('Root',0,-1),('Pelvis',2,0),('Spine',3,1),('Neck',40,2),('Head',43,3),('LClav',53,2),('LArm',54,5),('LFore',55,6),('LHand',56,7),('RClav',74,2),('RArm',75,9),('RFore',76,10),('RHand',77,11),('LThigh',4,1),('LCalf',5,13),('LFoot',6,14),('RThigh',22,1),('RCalf',23,16),('RFoot',24,17)]
names=['BIP01','BIP01 PELVIS','BIP01 SPINE2','BIP01 NECK','BIP01 HEAD','BIP01 L CLAVICLE','BIP01 L UPPERARM','BIP01 L FOREARM','BIP01 L HAND','BIP01 R CLAVICLE','BIP01 R UPPERARM','BIP01 R FOREARM','BIP01 R HAND','BIP01 L THIGH','BIP01 L CALF','BIP01 L FOOT','BIP01 R THIGH','BIP01 R CALF','BIP01 R FOOT']
roots=[next(i for i,j in enumerate(joints) if j['name'].upper()==n) for n in names];lookup={r:k for k,r in enumerate(roots)}
def group(i):return lookup[i] if i in lookup else group(joints[i]['parent']) if joints[i]['parent']>=0 else 0
vec=lambda p:Vector((p.x,p.y,p.z))
for stem,armor,headname,bodytex,skin,face,teeth in [('cx_gorn','HUM_SLDM_ARMOR.MDM','HUM_HEAD_FIGHTER.MMB',0,3,13,0),('cx_milten','HUM_KDFL_ARMOR.MDM','HUM_HEAD_BALD.MMB',0,1,76,1),('cx_lester','HUM_NOVM_ARMOR.MDM','HUM_HEAD_BALD.MMB',1,0,17,2),('cx_xardas','HUM_DMBM_ARMOR.MDM','HUM_HEAD_BALD.MMB',0,1,82,1),('cx_thorus','HUM_GRDS_ARMOR.MDM','HUM_HEAD_FIGHTER.MMB',0,3,12,0)]:
 geoms=[];body=ModelMesh.load(asset(armor));head=MorphMesh.load(asset(headname))
 def add(mesh,weights,is_head=False):
  pos=[vec(p) for p in mesh.positions]
  for sub in mesh.submeshes:
   texture=sub.material.texture.upper()
   if texture.startswith('HUM_BODY_NAKED'):texture=f'HUM_BODY_NAKED_V{bodytex}_C{skin}.TGA'
   if texture.startswith('HUM_HEAD_V'):texture=f'HUM_HEAD_V{face}_C{skin}.TGA'
   if texture.startswith('HUM_TEETH_V'):texture=f'HUM_TEETH_V{teeth}.TGA'
   if not texture:raise RuntimeError((stem,sub.material.name))
   verts=[];normals=[];uv=[];ww=[]
   for w in sub.wedges:
    p=pos[w.index];n=vec(w.normal)
    if is_head:p=world[6]@p;n=world[6].to_3x3()@n;chosen=[(4,1)]
    else:
     g=collections.defaultdict(float)
     for weight in weights[w.index]:g[group(weight.index)]+=weight.weight
     chosen=sorted(g.items(),key=lambda x:x[1],reverse=True)[:2];total=sum(q for k,q in chosen);chosen=[(k,q/total) for k,q in chosen]
    verts.append(p);normals.append(n);uv.append((w.texture.x,w.texture.y));ww.append(chosen)
   geoms.append(dict(vertices=verts,normals=normals,uv=uv,weights=ww,faces=[list(t.wedges) for t in sub.triangles],texture=texture))
 for mesh in body.meshes:add(mesh.mesh,mesh.weights)
 add(head.mesh,None,True)
 regions={}
 for g in geoms:
  texture=g['texture'];regions.setdefault(texture,[]).extend(g['uv'])
 images=[]
 for name,uv in regions.items():
  tex=Texture.load(asset(name.replace('.TGA','-C.TEX')));im=Image.frombytes('RGBA',(tex.width,tex.height),tex.mipmap_rgba(0)).convert('RGB');lo=[math.floor(min(p[k] for p in uv)) for k in range(2)];hi=[math.ceil(max(p[k] for p in uv)) for k in range(2)];images.append((name,im,lo,hi,(hi[0]-lo[0])*im.width,(hi[1]-lo[1])*im.height))
 for size in [1024,2048]:
  atlas=Image.new('RGB',(size,size),(20,15,10));layouts={};x=y=rh=0;fit=True
  for name,im,lo,hi,w,h in sorted(images,key=lambda a:a[-1],reverse=True):
   if x+w>size:x=0;y+=rh;rh=0
   if y+h>size or w>size:fit=False;break
   for a in range(hi[0]-lo[0]):
    for b in range(hi[1]-lo[1]):atlas.paste(im,(x+a*im.width,y+b*im.height))
   layouts[name]=(x-lo[0]*im.width,y-lo[1]*im.height,im.width,im.height);x+=w;rh=max(rh,h)
  if fit:break
 assert fit
 ground=min(p.y for g in geoms for p in g['vertices']);top=max(p.y for g in geoms for p in g['vertices']);factor=56/(top-ground);turn=Matrix.Rotation(math.pi,4,'Y');norm=lambda p:turn@((p-Vector((0,ground,0)))*factor)
 model=dict(vertices=[],normals=[],uv=[],weights=[],faces=[],bones=[dict(name=n,native=b,parent=par,pivot=list(norm(world[j].translation))) for (n,b,par),j in zip(defs,roots)])
 for g in geoms:
  off=len(model['vertices']);model['vertices'].extend(list(norm(p)) for p in g['vertices']);model['normals'].extend(list(turn.to_3x3()@p) for p in g['normals']);ox,oy,tw,th=layouts[g['texture']];model['uv'].extend(((ox+u*tw)/size,1-(oy+v*th)/size) for u,v in g['uv']);model['weights'].extend(g['weights']);model['faces'].extend([i+off for i in f] for f in g['faces'])
 target=P/'pack';(target/'Data/Textures').mkdir(parents=True,exist_ok=True);atlas.save(target/'Data/Textures'/(stem+'.png'));(P/(stem+'-skin-model.json')).write_text(json.dumps(model));print('GOTHIC MEME',stem,export_skin(model,stem,target),len(model['faces']),flush=True)
