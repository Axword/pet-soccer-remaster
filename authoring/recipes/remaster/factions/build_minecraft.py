"""Original Mojang Bedrock geometry plus official Java 1.21.4 textures.
Rigid voxel limbs use one adapter per original pivot; football timing is unchanged.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,math,zipfile
from mathutils import Vector,Matrix
R=pathlib.Path(__file__).parent;P=R.parent.parent;sys.path.insert(0,str(P/'tools/python'));sys.path.insert(0,str(R))
from PIL import Image
from export_skinned_character import export_skin
OUT=R/'pack';SRC=R/'sources/minecraft';MODELS=SRC/'models'
DEFS=[('Root',0,-1),('Pelvis',2,0),('Spine',3,1),('Neck',40,2),('Head',43,3),('LClav',53,2),('LArm',54,5),('LFore',55,6),('LHand',56,7),('RClav',74,2),('RArm',75,9),('RFore',76,10),('RHand',77,11),('LThigh',4,1),('LCalf',5,13),('LFoot',6,14),('RThigh',22,1),('RCalf',23,16),('RFoot',24,17)]
def build(name):
 file='humanoid.custom' if name in ['steve','alex'] else name;j=json.loads((MODELS/(file+'.geo.json')).read_text());geo=j['minecraft:geometry'][0] if 'minecraft:geometry' in j else next(v for k,v in j.items() if k.startswith('geometry.'))
 bones=geo['bones'];allbones={b['name']:b for b in bones};defs=list(DEFS);pivots=[(0,0,0),(0,12,0),(0,24,0),(0,24,0),(0,24,0),(4,22,0),(6,22,0),(6,16,0),(6,12,0),(-4,22,0),(-6,22,0),(-6,16,0),(-6,12,0),(2,12,0),(2,6,0),(2,0,0),(-2,12,0),(-2,6,0),(-2,0,0)]
 if name=='creeper':
  # Four independent source pivots; diagonal pairs reuse the existing two
  # thigh rotations. Every leg attaches directly to the visible rigid body.
  defs[13]=('LThigh',4,2);defs[16]=('RThigh',22,2)
  defs.extend([('RearRightLeg',4,2),('RearLeftLeg',22,2)])
  pivots.extend([tuple(allbones['leg2']['pivot']),tuple(allbones['leg3']['pivot'])])
 def group(label):
  lower=label.lower()
  if any(n in lower for n in ['head','hat','nose']):return 4
  if lower in ['leg0','leg1','leg2','leg3']:return {'leg0':16,'leg1':13,'leg2':19,'leg3':20}[lower]
  if 'leftarm' in lower:return 6
  if 'rightarm' in lower:return 10
  if 'leftleg' in lower:return 13
  if 'rightleg' in lower:return 16
  if 'body' in lower or lower=='arms':return 2
  if 'waist' in lower:return 1
  par=allbones[label].get('parent');return group(par) if par else 2
 for b in bones:
  g=group(b['name'])
  if g in [4,6,10,13,16,19,20] and 'pivot' in b:pivots[g]=tuple(b['pivot'])
 if name=='creeper':pivots[2]=(0,6,0);pivots[1]=(0,6,0)
 if name=='enderman':
  # Bake a coherent Java-like neutral pose from original Bedrock cuboids.
  # Raw Bedrock geometry expects a separate base-pose animation: its head
  # needs +14Y and its right arm -2X before use as a standalone bind mesh.
  pivots=[(0,0,0),(0,26,0),(0,32,0),(0,38,0),(0,38,0),(4,36,0),(5,36,0),(5,22,0),(5,8,0),(-4,36,0),(-5,36,0),(-5,22,0),(-5,8,0),(2,26,0),(2,11,0),(2,-4,0),(-2,26,0),(-2,11,0),(-2,-4,0)]
  defs[13]=('LThigh',4,2);defs[16]=('RThigh',22,2)
 vs=[];normals=[];uv=[];faces=[];weights=[]
 texture_path={'steve':'player/wide/steve.png','alex':'player/slim/alex.png','villager':'villager/villager.png','zombie':'zombie/zombie.png','skeleton':'skeleton/skeleton.png','creeper':'creeper/creeper.png','enderman':'enderman/enderman.png'}[name]
 with zipfile.ZipFile(SRC/'client-1.21.4.jar') as z:im=Image.open(__import__('io').BytesIO(z.read('assets/minecraft/textures/entity/'+texture_path))).convert('RGBA')
 if name=='enderman':
  with zipfile.ZipFile(SRC/'client-1.21.4.jar') as z:
   eyes=Image.open(__import__('io').BytesIO(z.read('assets/minecraft/textures/entity/enderman/enderman_eyes.png'))).convert('RGBA');im.alpha_composite(eyes)
 # Bedrock skeleton UVs match 64x32 Java; Villager base has no clothing overlay.
 tw=geo.get('texturewidth',geo.get('description',{}).get('texture_width',64));th=geo.get('textureheight',geo.get('description',{}).get('texture_height',64))
 if name in ['creeper','skeleton','enderman']:th=32
 else:th=64
 def cube(b,c):
  if b.get('neverRender',False):return
  if (c.get('inflate',0)>0 and name!='villager') or (b['name']=='hat' and name!='enderman') or b['name'] in ['leftSleeve','rightSleeve','leftPants','rightPants','jacket']:return
  lo=list(c['origin']);size=list(c['size']);a,bb=c.get('uv',[0,0]);x0,y0,z0=lo;w,h,d=size;x1,y1,z1=x0+w,y0+h,z0+d
  if name=='enderman':
   if b['name']=='head':y0+=14;y1+=14
   if b['name']=='rightArm':x0-=2;x1-=2
  if name=='alex' and b['name'] in ['leftArm','rightArm']:
   # Mojang's slim skin model differs by one pixel arm width.
   w=3;x1=x0+w
  qs=[([(x0,y1,z0),(x1,y1,z0),(x1,y0,z0),(x0,y0,z0)],(a+d,bb+d,w,h)), ([(x1,y1,z1),(x0,y1,z1),(x0,y0,z1),(x1,y0,z1)],(a+2*d+w,bb+d,w,h)), ([(x0,y1,z1),(x0,y1,z0),(x0,y0,z0),(x0,y0,z1)],(a,bb+d,d,h)), ([(x1,y1,z0),(x1,y1,z1),(x1,y0,z1),(x1,y0,z0)],(a+d+w,bb+d,d,h)), ([(x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0)],(a+d,bb,w,d)), ([(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],(a+d+w,bb,w,d))]
  g=group(b['name']);rot=c.get('rotation',b.get('rotation',[0,0,0]));pivot=Vector(pivots[g] if name=='enderman' else c.get('pivot',b.get('pivot',[0,0,0])));m=Matrix.Identity(4)
  if name=='zombie' and 'arm' in b['name'].lower():rot=[-75,0,0]
  for axis,angle in zip('XYZ',rot):m=m@Matrix.Rotation(-math.radians(angle),4,axis)
  inflate=c.get('inflate',0)
  if inflate:
   center=Vector(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2));qs=[([list(center+Vector(((p[0]-center.x)*(w+2*inflate)/w,(p[1]-center.y)*(h+2*inflate)/h,(p[2]-center.z)*(d+2*inflate)/d))) for p in q],rect) for q,rect in qs]
  for q,rect in qs:
   pp=[pivot+m.to_3x3()@(Vector(p)-pivot) for p in q];normal=(pp[1]-pp[0]).cross(pp[2]-pp[0]).normalized();xx,yy,ww,hh=rect
   coords=[(xx/tw,1-yy/th),((xx+ww)/tw,1-yy/th),((xx+ww)/tw,1-(yy+hh)/th),(xx/tw,1-(yy+hh)/th)]
   if c.get('mirror',b.get('mirror',False)):coords=[coords[1],coords[0],coords[3],coords[2]]
   def emit(points,texcoords):
    off=len(vs);vs.extend(map(list,points));normals.extend([list(normal)]*4);uv.extend(texcoords);weights.extend([[(g,1)]]*4);faces.extend([[off,off+1,off+2],[off,off+2,off+3]])
   if name!='skeleton':emit(pp,coords);continue
   # Geometric cutout as well as retained RGBA: even a legacy opaque native
   # material cannot fill the actual spaces between the original pixel ribs.
   def interp(values,s,t):return values[0].lerp(values[1],s).lerp(values[3].lerp(values[2],s),t)
   tc=[Vector(v) for v in coords]
   for row in range(int(hh)):
    for col in range(int(ww)):
     s0=col/ww;s1=(col+1)/ww;t0=row/hh;t1=(row+1)/hh;mid=interp(tc,(s0+s1)/2,(t0+t1)/2)
     px=min(im.width-1,max(0,int(mid.x*tw)));py=min(im.height-1,max(0,int((1-mid.y)*th)))
     if im.getpixel((px,py))[3]<128:continue
     fractions=[(s0,t0),(s1,t0),(s1,t1),(s0,t1)];emit([interp(pp,s,t) for s,t in fractions],[tuple(interp(tc,s,t)) for s,t in fractions])
 for b in bones:
  for c in b.get('cubes',[]):cube(b,c)
 bottom=min(v[1] for v in vs);top=max(v[1] for v in vs);height={'steve':56,'alex':55,'zombie':56,'skeleton':56,'creeper':48,'enderman':76,'villager':58}[name];factor=height/(top-bottom)
 norm=lambda v:[v[0]*factor,(v[1]-bottom)*factor,v[2]*factor]
 model=dict(vertices=[norm(v) for v in vs],normals=normals,uv=uv,faces=faces,weights=weights,bones=[dict(name=n,native=b,parent=p,pivot=norm(v)) for (n,b,p),v in zip(defs,pivots)])
 stem='cx_mc_'+name;(R/(stem+'-skin-model.json')).write_text(json.dumps(model));(OUT/'Data/Textures').mkdir(parents=True,exist_ok=True)
 # Compose Villager's original plains clothing/profession overlay, alpha in source.
 if name=='villager':
  with zipfile.ZipFile(SRC/'client-1.21.4.jar') as z:
   extra=Image.open(__import__('io').BytesIO(z.read('assets/minecraft/textures/entity/villager/type/plains.png'))).convert('RGBA');im.alpha_composite(extra)
 # Preserve source transparency, including Skeleton's original rib gaps.
 im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST).save(OUT/'Data/Textures'/(stem+'.png'));print('MINECRAFT',name,export_skin(model,stem,OUT),'faces',len(faces),flush=True)
for name in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['steve','alex','zombie','skeleton','creeper','enderman','villager']:build(name)
