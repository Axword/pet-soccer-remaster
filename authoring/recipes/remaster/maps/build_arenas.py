"""Native static arena backdrops and conservative binary map aliases.

Run with Blender's Python (Pillow added from the existing local tools directory).
All writes stay in this task's directory; no game copy is touched.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,math,random,struct,json,re,shutil,collections
O=pathlib.Path(__file__).parent;P=O.parents[1];sys.path.insert(0,str(P/'tools/python'));sys.path.insert(0,str(P))
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from mathutils import Vector
from inspect_3da import inspect
D=O/'Pack/Data';(D/'Meshes/Objects').mkdir(parents=True,exist_ok=True);(D/'Textures').mkdir(parents=True,exist_ok=True)
BASE=P/'PetSoccer-Meme-Test';SRC=BASE/'Data/Levels/Niedzwiedzie';TEMPLATE=(P/'cursor-reference.3da').read_bytes()
CENTER=[7502.9892578125,6.25,7520.986328125]
EXCLUSION=[-1900,-3300,1900,3300]

class Mesh:
 def __init__(self,name):self.name=name;self.v=[];self.n=[];self.uv=[];self.f=[];self.mi=[];self.materials=[];self.features=[]
 def material(self,name):
  if name not in self.materials:self.materials.append(name)
  return self.materials.index(name)
 def face(self,p,mat=0,uv=None):
  p=[Vector(v) for v in p];normal=(p[1]-p[0]).cross(p[2]-p[0]);ln=normal.length
  if ln<1e-7:return
  normal/=ln;start=len(self.v);self.v.extend(map(list,p));self.n.extend([list(normal)]*len(p));self.uv.extend(uv or [(0,0),(1,0),(1,1),(0,1)][:len(p)])
  for j in range(1,len(p)-1):self.f.append((start,start+j,start+j+1));self.mi.append(mat)
 def box(self,lo,hi,mat=0):
  a,b,c=lo;x,y,z=hi
  for f in [[(a,y,c),(x,y,c),(x,b,c),(a,b,c)],[(x,y,z),(a,y,z),(a,b,z),(x,b,z)],[(a,y,z),(a,y,c),(a,b,c),(a,b,z)],[(x,y,c),(x,y,z),(x,b,z),(x,b,c)],[(a,y,z),(x,y,z),(x,y,c),(a,y,c)],[(a,b,c),(x,b,c),(x,b,z),(a,b,z)]]:self.face(f,mat)
 def loft(self,rows,mat=0,sides=8):
  rings=[[(x+rx*math.cos(i*math.tau/sides),y,z+rz*math.sin(i*math.tau/sides)) for i in range(sides)] for x,y,z,rx,rz in rows]
  for a,b in zip(rings,rings[1:]):
   for j in range(sides):self.face([a[j],b[j],b[(j+1)%sides],a[(j+1)%sides]],mat)
  self.face(rings[0],mat,[(0,0)]*sides);self.face(rings[-1][::-1],mat,[(0,0)]*sides)
 def rod(self,a,b,r,mat=0,sides=6):
  a=Vector(a);b=Vector(b);axis=(b-a).normalized();right=axis.cross(Vector((0,0,1)))
  if right.length<.1:right=axis.cross(Vector((1,0,0)))
  right.normalize();up=axis.cross(right);low=[a+r*(right*math.cos(i*math.tau/sides)+up*math.sin(i*math.tau/sides)) for i in range(sides)];high=[p+b-a for p in low]
  for i in range(sides):self.face([low[i],high[i],high[(i+1)%sides],low[(i+1)%sides]],mat)
  self.face(low,mat,[(0,0)]*sides);self.face(high[::-1],mat,[(0,0)]*sides)
 def transformed(self,fn,start=0):
  for i in range(start,len(self.v)):self.v[i]=list(fn(Vector(self.v[i])))
  # Refresh face normals after a rigid/uniform transform.
  for f in self.f:
   if f[0]>=start:
    a,b,c=[Vector(self.v[i]) for i in f];n=(b-a).cross(c-a).normalized()
    for i in f:self.n[i]=list(n)
 def mark(self,kind,**kw):self.features.append(dict(kind=kind,**kw))

def texture(stem,kind,base,seed=1,pixel=False):
 rng=random.Random(seed);size=16 if pixel else 256;im=Image.new('RGB',(size,size));px=im.load()
 for y in range(size):
  for x in range(size):
   n=rng.randint(-16,16) if pixel else rng.randint(-10,10)+int(6*math.sin(x*.06)*math.sin(y*.035));px[x,y]=tuple(max(0,min(255,v+n)) for v in base)
 d=ImageDraw.Draw(im)
 if kind in ['stone','brick','cobble']:
  cell=4 if pixel else 48
  for y in range(0,size,cell):
   for x in range(-cell,size,cell):
    x+=cell//2*((y//cell)%2);variation=rng.randrange(-16,17);c=tuple(max(0,min(255,v+variation)) for v in base);d.rounded_rectangle((x+1,y+1,x+cell-1,y+cell-1),0 if pixel else 4,fill=c,outline=tuple(int(v*.6) for v in c),width=1 if pixel else 2)
 elif kind in ['wood','planks','bark']:
  step=4 if pixel else 48
  for x in range(0,size,step):
   d.line((x,0,x,size),fill=tuple(int(v*.6) for v in base),width=1 if pixel else 3)
   if not pixel:
    for j in range(9):
     xx=x+rng.randrange(3,step-3);yy=rng.randrange(size);d.line([(xx,yy),(xx+rng.randrange(-3,4),yy+45)],fill=tuple(int(v*.75) for v in base),width=1)
  if kind=='planks':
   for y in range(0,size,step*2):d.line((0,y,size,y),fill=tuple(int(v*.6) for v in base),width=1 if pixel else 2)
 elif kind=='roof':
  cell=4 if pixel else 32
  for y in range(0,size,cell):
   for x in range(-cell,size,cell):d.arc((x+(cell//2 if y//cell%2 else 0),y-cell//2,x+cell,y+cell),0,180,fill=tuple(int(v*.5) for v in base),width=1 if pixel else 2)
 elif kind=='leaves':
  for _ in range(90 if pixel else 1600):
   x,y=rng.randrange(size),rng.randrange(size);r=1 if pixel else rng.randrange(2,10);c=tuple(max(0,min(255,v+rng.randrange(-35,36))) for v in base);d.rectangle((x,y,x+r,y+r),fill=c)
 elif kind=='metal':
  for x in range(0,size,4 if pixel else 24):d.line((x,0,x,size),fill=tuple(int(v*.6) for v in base),width=1 if pixel else 3)
  if not pixel:
   for _ in range(120):x,y=rng.randrange(size),rng.randrange(size);d.ellipse((x,y,x+rng.randrange(2,14),y+rng.randrange(2,25)),fill=(99+rng.randrange(30),64,38))
 if pixel:im=im.resize((256,256),Image.Resampling.NEAREST)
 im.save(D/'Textures'/(stem+'.png'));return stem+'.png'

def mats(m,ident,theme):
 palettes={
 'gothic':[(104,97,82),(80,56,35),(89,85,73),(76,91,52),(139,109,74),(63,57,45),(176,163,132)],
 'rift':[(101,117,116),(71,80,62),(70,84,83),(37,87,72),(135,112,64),(41,66,77),(80,161,184)],
 'kaer':[(120,123,120),(85,65,44),(83,89,100),(35,65,56),(137,125,102),(63,66,74),(164,170,173)],
 'minecraft':[(125,127,121),(123,91,51),(123,91,51),(72,131,46),(142,102,65),(91,107,118),(159,177,199)],
 'sejm':[(214,210,192),(130,82,43),(42,82,61),(74,96,77),(151,105,58),(184,182,172),(225,227,211)],
 'bklasa':[(134,124,111),(111,91,60),(91,99,92),(74,105,51),(147,100,65),(92,100,106),(175,174,157)]}
 kinds=['stone','wood','roof','leaves','brick','metal','plain'];out=[]
 for j,(base,kind) in enumerate(zip(palettes[theme],kinds)):out.append(m.material(texture(f'cx{ident}_{j:02}',kind,base,ident*13+j,theme=='minecraft')))
 return out

def roof(m,x,y,z,w,depth,height,mat):
 a=(x-w,y,z-depth);b=(x+w,y,z-depth);c=(x,y+height,z-depth);aa=(x-w,y,z+depth);bb=(x+w,y,z+depth);cc=(x,y+height,z+depth)
 m.face([a,b,c],mat,[(0,0),(1,0),(.5,1)]);m.face([bb,aa,cc],mat,[(0,0),(1,0),(.5,1)]);m.face([a,c,cc,aa],mat);m.face([c,b,bb,cc],mat)
def round_tower(m,x,z,r,h,stone,roofmat,broken=False):
 m.loft([(x,-35,z,r*1.2,r*1.2),(x,90,z,r*1.2,r*1.2),(x,160,z,r,r),(x,h,z,r*.94,r*.94)],stone,12)
 for y in [h*.4,h*.72,h-80]:m.loft([(x,y,z,r*1.01,r*1.01),(x,y+35,z,r*1.01,r*1.01)],stone,12)
 if broken:
  for i in range(9):
   a=i*math.tau/12;m.box((x+math.cos(a)*r-50,h,z+math.sin(a)*r-50),(x+math.cos(a)*r+50,h+95+(i%3)*15,z+math.sin(a)*r+50),stone)
 else:m.loft([(x,h,z,r*1.15,r*1.15),(x,h+300,z,8,8)],roofmat,12)
def tree(m,x,z,size,wood,leaf,rng,style='pine'):
 y=0;m.rod((x,-40,z),(x+size*.06,size*.85,z),size*.055,wood,6)
 if style=='oak':
  for dx,dz,h,r in [(-.22,.06,.65,.37),(.2,-.12,.85,.41),(0,.18,1.04,.39)]:m.loft([(x+dx*size,size*h-size*.12,z+dz*size,r*size,r*size),(x+dx*size,size*h+size*.18,z+dz*size,r*.75*size,r*.75*size),(x+dx*size,size*h+size*.27,z+dz*size,.08*size,.08*size)],leaf,7)
 else:
  for j in range(4):
   y=size*(.3+j*.19);r=size*(.32-j*.055);m.loft([(x,y,z,r,r),(x+size*.02,y+size*.36,z+size*.03,size*.025,size*.025)],leaf,7)
def rock(m,x,z,s,h,mat,rng):
 a=rng.uniform(0,math.tau);sides=7;rows=[]
 for y,r in [(-50,1),(h*.25,1.05),(h*.7,.7),(h,.15)]:rows.append((x+math.sin(a)*y*.08,y,z+math.cos(a)*y*.08,s*r,s*r*.75))
 m.loft(rows,mat,sides)
def wall(m,a,b,height,thickness,mat,crenel=False):
 # Axis-aligned wall with visible courses and optional battlements.
 x0,z0=a;x1,z1=b
 m.box((min(x0,x1)-thickness/2,-50,min(z0,z1)-thickness/2),(max(x0,x1)+thickness/2,height,max(z0,z1)+thickness/2),mat)
 if crenel:
  n=max(2,int(math.hypot(x1-x0,z1-z0)/180))
  for j in range(n+1):
   x=x0+(x1-x0)*j/n;z=z0+(z1-z0)*j/n;m.box((x-55,height,z-55),(x+55,height+90,z+55),mat)
def plank_hut(m,x,z,w,d,h,wood,roofmat,stone,lean=0):
 m.box((x-w,-30,z-d),(x+w,50,z+d),stone);m.box((x-w,40,z-d),(x+w,h,z+d),wood);roof(m,x,h,z,w+35,d+35,h*.5,roofmat)
 m.box((x-w*.23,40,z-d-3),(x+w*.23,h*.72,z-d-1),stone)
 for dx in [-w*.65,w*.65]:m.box((x+dx-42,h*.45,z-d-7),(x+dx+42,h*.72,z-d-2),stone)
 m.mark('timber_hut',x=x,z=z,width=w*2,height=h*1.5)

def add_oldcamp(m,ids):
 source=json.loads((O/'source/oldcamp-source.json').read_text());texmap={};seen={}
 for key,t in source['materials'].items():
  filename=t.rsplit('.',1)[0].upper()+'-C.TEX.png';old=O/'source'/filename
  if not old.exists():continue
  if filename not in seen:
   name=f'cx38_g{len(seen):02}.png';im=Image.open(old).convert('RGB');im.thumbnail((512,512));im.save(D/'Textures'/name);seen[filename]=m.material(name)
  texmap[int(key)]=seen[filename]
 polygons=[p for p in source['polygons'] if p[0] in texmap]
 used=[source['positions'][i] for _,p,_ in polygons for i in p];lo=[min(v[k] for v in used) for k in range(3)];hi=[max(v[k] for v in used) for k in range(3)];mid=[(a+b)/2 for a,b in zip(lo,hi)];factor=.43
 for mat,indices,features in polygons:
  pts=[];uv=[]
  for i,j in zip(indices,features):
   x,y,z=source['positions'][i];pts.append((4700-(z-mid[2])*factor,(y-lo[1])*factor-40,(x-mid[0])*factor+500));uv.append(source['features'][j]['uv'])
  # Gothic world polygons use clockwise winding relative to their stored normals.
  # The Pet Soccer writer uses the outward cross-product convention.
  m.face(pts[::-1],texmap[mat],uv[::-1])
 m.mark('actual_Gothic_WORLD_ZEN_Old_Camp_castle',source_bounds=lo+hi,scale=factor,source_triangles=sum(len(p)-2 for _,p,_ in polygons))

def build_gothic():
 m=Mesh('CXarena38');stone,wood,roofmat,leaf,brick,metal,cream=mats(m,38,'gothic');rng=random.Random(38)
 # Keep material slots available for 27 genuine Gothic source textures.
 m.materials=m.materials[:4];wood=1;stone=0;roofmat=2;leaf=3;add_oldcamp(m,(stone,wood))
 crag=m.material(texture('cx38_crag','plain',(91,89,80),3811))
 # Palisades: perimeter framing, varied pointed trunks, tied horizontal beams.
 for x0,z0,x1,z1 in [(-2400,-3900,-2400,3900),(-2400,-3900,2300,-3900),(-2400,3900,2300,3900)]:
  n=int(math.hypot(x1-x0,z1-z0)/110)
  for i in range(n+1):
   x=x0+(x1-x0)*i/n;z=z0+(z1-z0)*i/n;h=420+rng.randrange(-45,65);m.loft([(x,-70,z,48,48),(x,h-85,z,46,46),(x,h,z,3,3)],wood,5)
  for h in [110,295]:m.rod((x0,h,z0),(x1,h,z1),23,wood,6)
 for x,z,w,d,h in [(-3550,-2300,480,330,350),(-3700,0,570,400,390),(-3450,2300,450,390,350),(800,-4850,590,430,430),(-1000,4750,520,370,330)]:plank_hut(m,x,z,w,d,h,wood,roofmat,stone)
 for x,z in [(-2450,-3900),(-2450,3900),(2400,-3900),(2400,3900)]:
  for dx,dz in [(-100,-100),(-100,100),(100,-100),(100,100)]:m.rod((x+dx,-40,z+dz),(x+dx,700,z+dz),35,wood)
  m.box((x-220,550,z-220),(x+220,625,z+220),wood);roof(m,x,790,z,270,270,250,roofmat)
 for _ in range(30):
  x=rng.choice([-1,1])*rng.uniform(5000,6500);z=rng.uniform(-6100,6100);rock(m,x,z,rng.uniform(300,800),rng.uniform(600,1500),crag,rng)
 m.mark('Old_Camp_palisade_huts_watchtowers');return m

def crystal(m,x,z,y,r,h,mat):
 m.loft([(x,y,z,r*.65,r*.65),(x,y+h*.22,z,r,r),(x+r*.16,y+h*.78,z,r*.6,r*.6),(x+r*.1,y+h,z,2,2)],mat,6)
def build_rift():
 m=Mesh('CXarena39');stone,wood,roofmat,leaf,gold,metal,cyan=mats(m,39,'rift');rng=random.Random(39)
 crag=m.material(texture('cx39_crag','plain',(78,103,95),3911))
 blue=m.material(texture('cx39_blue','plain',(43,161,218),91));red=m.material(texture('cx39_red','plain',(191,62,87),92));water=m.material(texture('cx39_water','plain',(48,126,140),93))
 for z,magic in [(-4350,blue),(4350,red)]:
  m.loft([(0,-40,z,950,680),(0,70,z,950,680),(0,125,z,790,570)],stone,16)
  for angle in range(0,360,45):
   a=math.radians(angle);x=math.sin(a)*620;zz=z+math.cos(a)*440;crystal(m,x,zz,100,90,340,magic)
  m.loft([(0,125,z,420,300),(0,250,z,350,260)],gold,10);crystal(m,0,z,240,300,980,magic)
  for side in [-1,1]:
   for i in range(3):m.rod((side*500,100,z+250),(side*(560+i*30),280+i*85,z+80),45,stone,6)
 for x,z,magic in [(-2350,-3000,blue),(2350,-3000,blue),(-2350,3000,red),(2350,3000,red)]:
  m.loft([(x,-40,z,260,260),(x,100,z,260,260),(x,170,z,200,200),(x,640,z,130,130),(x,730,z,210,210)],stone,8)
  m.loft([(x,540,z,165,165),(x,600,z,165,165)],gold,8);crystal(m,x,z,740,135,330,magic)
  for s in [-1,1]:m.rod((x+s*150,520,z),(x+s*235,830,z),45,gold,6)
 # A separate river bank curves beside the jungle; never across the football field.
 for j in range(15):
  z=-3600+j*500;x=-3250+180*math.sin(j*.5);m.box((x-330,-18,z-260),(x+330,-11,z+260),water)
  for side in [-1,1]:rock(m,x+side*470,z,rng.uniform(140,280),rng.uniform(180,430),crag,rng)
 for side in [-1,1]:
  for j in range(11):
   z=-3300+j*660;x=side*(3350+rng.randrange(0,900));rock(m,x,z,350+rng.randrange(300),450+rng.randrange(600),crag,rng)
   tree(m,x+side*400,z+120,750+rng.randrange(500),wood,leaf,rng)
  for z in [-5450,5450]:
   for j in range(6):tree(m,side*(1300+j*500),z+rng.randrange(-300,300),850+rng.randrange(450),wood,leaf,rng)
 m.mark('opposing_blue_red_Nexus_bases');m.mark('four_stone_crystal_turrets');m.mark('jungle_rock_walls_and_side_river');return m

def build_kaer():
 m=Mesh('CXarena40');stone,wood,roofmat,leaf,brick,metal,cream=mats(m,40,'kaer');rng=random.Random(40)
 crag=m.material(texture('cx40_crag','plain',(100,106,111),4011))
 # Castle on the eastern escarpment: blunt great tower, broken outer wall, long keep.
 for x,z,s,h in [(4800,200,1500,1100),(5100,-2100,1400,1500),(5350,2400,1500,900)]:rock(m,x,z,s,h,crag,rng)
 base=820;m.box((3750,base-100,-1700),(5450,base+1400,1200),stone);roof(m,4600,base+1400,-250,925,1550,800,roofmat)
 # Recessed tall windows and wooden gallery are structural, not colored dots.
 for z in [-1250,-550,150,850]:
  m.box((3735,base+500,z-80),(3750,base+1050,z+80),metal);m.box((3630,base+410,z-180),(3755,base+455,z+180),wood)
  for zz in [z-120,z+120]:m.rod((3610,base+420,zz),(3740,base+120,zz),22,wood)
 round_tower(m,3650,-1950,520,base+1800,stone,roofmat,True);round_tower(m,5650,1550,440,base+1600,stone,roofmat,False)
 round_tower(m,6200,-1500,620,base+2450,stone,roofmat,True)
 wall(m,(2700,-3000),(6200,-3000),base+650,140,stone,True);wall(m,(2700,3000),(6200,3000),base+550,140,stone,True)
 wall(m,(2700,-3000),(2700,-1500),base+450,140,stone,True);wall(m,(2700,1500),(2700,3000),base+450,140,stone,True)
 for x,z in [(2700,-3000),(2700,3000)]:round_tower(m,x,z,330,base+950,stone,roofmat,True)
 # Inclined approach, scaffolding, stone stair silhouette.
 for j in range(8):m.box((2350+j*130,base-650+j*85,-800),(2480+j*130,base-565+j*85,500),stone)
 for z in [-1000,-350,300,950]:
  m.rod((3500,base-100,z),(3500,base+700,z),25,wood);m.rod((3500,base,z),(3900,base+650,z+500),24,wood)
 for side in [-1,1]:
  for j in range(18):
   x=side*rng.uniform(3500,7200);z=rng.uniform(-6500,6500)
   if side==1 and abs(z)<3200:continue
   tree(m,x,z,rng.uniform(600,1300),wood,leaf,rng)
 for x,z in [(-4500,-6500),(-1500,-7000),(1500,-7200),(6500,6500),(-6000,6500)]:rock(m,x,z,1700,2300+rng.randrange(1500),crag,rng)
 m.mark('asymmetrical_Kaer_Morhen_keep_cliff_broken_towers');m.mark('wooden_gallery_scaffold_mountain_pines');return m

def mcbox(m,lo,hi,side,top=None):
 start=len(m.f);m.box(lo,hi,side)
 if top is not None:
  for i in [start+8,start+9]:m.mi[i]=top
def mctree(m,x,z,wood,leaf,size=160):
 m.box((x-size*.5,-40,z-size*.5),(x+size*.5,size*4,z+size*.5),wood)
 for yy,w in [(3,2.2),(4,2.2),(5,1.3)]:m.box((x-w*size,yy*size,z-w*size),(x+w*size,(yy+1)*size,z+w*size),leaf)
def mc_house(m,x,z,w,d,wood,stone,roofmat,glass):
 u=160;m.box((x-w,-20,z-d),(x+w,2*u,z+d),stone);m.box((x-w,2*u,z-d),(x+w,4*u,z+d),wood)
 for s in [-1,1]:m.box((x+s*(w-u*.25)-u*.25,0,z-d-u*.1),(x+s*(w-u*.25)+u*.25,4*u,z+d+u*.1),wood)
 for j in range(4):m.box((x-w-u+j*u,4*u+j*u*.5,z-d-u),(x+w+u-j*u,4*u+(j+1)*u*.5,z+d+u),roofmat)
 m.box((x-u*.45,0,z-d-2),(x+u*.45,2*u,z-d-1),roofmat)
 for side in [-1,1]:m.box((x+side*w*.6-u*.45,2.2*u,z-d-3),(x+side*w*.6+u*.45,3.2*u,z-d-1),glass)
def build_minecraft():
 m=Mesh('CXarena41');stone,wood,roofmat,leaf,dirt,metal,glass=mats(m,41,'minecraft');rng=random.Random(41)
 grass=m.material(texture('cx41_grass','leaves',(93,154,54),777,True));water=m.material(texture('cx41_water','plain',(52,112,194),778,True));wheat=m.material(texture('cx41_wheat','leaves',(179,170,55),779,True))
 # A grid-coherent 200-unit block shelf rings the unchanged football rectangle.
 u=200
 for side in [-1,1]:
  for row in range(5):
   for j in range(42):
    x=side*(2200+row*u);z=-4100+j*u;h=40+row//2*u
    mcbox(m,(x-u*.5,-100,z-u*.5),(x+u*.5,h,z+u*.5),dirt,grass)
 for side in [-1,1]:
  for row in range(4):
   for j in range(20):
    x=-1900+j*u;z=side*(3700+row*u);mcbox(m,(x-u*.5,-100,z-u*.5),(x+u*.5,row*u*.6,z+u*.5),dirt,grass)
 for x,z,w,d in [(-4000,-2600,520,440),(-4300,1000,440,440),(3900,-2400,520,360),(3900,1900,500,480),(0,5200,600,420)]:mc_house(m,x,z,w,d,wood,stone,roofmat,glass)
 for x,z in [(-3800,3100),(-4500,-4200),(-3800,-900),(3700,3800),(4800,-1000),(-1200,-5600),(1800,-5900),(2500,5200),(-2300,5600)]:mctree(m,x,z,wood,leaf)
 for row in range(4):
  for j in range(10):
   x=-4000+row*180;z=2800+j*160;m.box((x-75,10,z-65),(x+75,80,z+65),wheat)
 for x,z,w,d in [(4100,-4900,1100,700),(-4300,5000,700,500)]:
  m.box((x-w,-50,z-d),(x+w,-40,z+d),water)
  for j in range(-3,4):mcbox(m,(x-w-200,-100,z+j*200-100),(x-w,150,z+j*200+100),dirt,grass)
 for x,z in [(-5400,-6100),(5700,6300),(-5900,6500)]:
  for j in range(4):mcbox(m,(x-900+j*180,-100,z-800+j*160),(x+900-j*180,300+j*300,z+800-j*160),dirt,grass)
 m.mark('Plains_Oak_forest_biome');m.mark('stepped_grass_dirt_blocks_oak_cobble_village_pond_wheat');return m

def rotated_box(m,lo,hi,x,z,angle,mat):
 start=len(m.v);m.box(lo,hi,mat);co,si=math.cos(angle),math.sin(angle);m.transformed(lambda p:(p.x*co+p.z*si+x,p.y,-p.x*si+p.z*co+z),start)
def build_sejm():
 m=Mesh('CXarena42');stone,wood,green,leaf,gold,metal,cream=mats(m,42,'sejm');rng=random.Random(42);seats=0
 # Horseshoe parliament seating at the three sides, with the whole centre open.
 for row in range(5):
  rx=2550+row*390;rz=3950+row*280;y=row*95
  for j in range(30):
   a=math.radians(18+j*324/29);x=rx*math.cos(a);z=rz*math.sin(a)
   if abs(x)<2200 and abs(z)<3600:continue
   seats+=1
   angle=-a+math.pi/2
   rotated_box(m,(-110,y,-75),(110,y+190,75),x,z,angle,wood)
   rotated_box(m,(-80,y+95,90),(80,y+115,245),x,z,angle,green)
   rotated_box(m,(-80,y+100,225),(80,y+290,265),x,z,angle,green)
 # Dais and presidential wood panel behind one goal, broad stone columns.
 m.box((-1500,-20,5700),(1500,230,6700),wood);m.box((-1250,230,5950),(1250,580,6400),wood)
 m.box((-350,230,5600),(350,700,5900),wood);m.box((-500,690,5520),(500,730,5940),wood)
 m.box((-1900,0,6850),(1900,2200,6990),wood)
 for x in range(-1800,1801,120):m.box((x,0,6830),(x+35,2200,6850),gold)
 white=m.material(texture('cx42_white','plain',(235,234,217),42));red=m.material(texture('cx42_red','plain',(179,40,49),43))
 for x in [-1450,1450]:
  m.rod((x,200,6200),(x,1900,6200),12,metal);m.face([(x,1850,6200),(x+340,1850,6200),(x+340,1500,6200),(x,1500,6200)],white);m.face([(x,1500,6200),(x+340,1500,6200),(x+340,1150,6200),(x,1150,6200)],red)
 for x in [-5000,5000]:
  for z in range(-5400,5401,900):
   m.loft([(x,-40,z,130,130),(x,1750,z,110,110)],cream,10);m.box((x-170,1730,z-170),(x+170,1840,z+170),stone)
  m.box((x-180,1820,-6000),(x+180,1990,6000),stone)
 m.mark('green_leather_hemicycle_wood_desks',seat_count=seats);m.mark('presidium_timber_wall_flags_columns_open_top');return m

def sign_texture(stem,text,bg,fg):
 im=Image.new('RGB',(512,128),bg);d=ImageDraw.Draw(im)
 try:font=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',44)
 except:font=ImageFont.load_default()
 bb=d.textbbox((0,0),text,font=font);d.text(((512-bb[2])/2,(128-bb[3])/2),text,font=font,fill=fg);d.rectangle((4,4,507,123),outline=fg,width=3);im.save(D/'Textures'/(stem+'.png'));return stem+'.png'
def build_bklasa():
 m=Mesh('CXarena43');stone,wood,roofmat,leaf,brick,metal,cream=mats(m,43,'bklasa');rng=random.Random(43)
 for side in [-1,1]:
  # Bent posts and uneven chain-link fencing. Horizontal strands are real geometry.
  x=side*2220
  for j in range(24):
   z=-3900+j*340;lean=rng.randrange(-55,56);m.rod((x,-50,z),(x+lean,310+rng.randrange(-30,31),z+rng.randrange(-35,36)),9,metal,5)
  for y in [50,145,250]:m.rod((x,y,-3900),(x,y,3920),3.5,metal,4)
  for j in range(70):
   z=-3900+j*110;m.rod((x,25,z),(x,280,z+250),1.8,metal,3);m.rod((x,280,z),(x,25,z+250),1.8,metal,3)
 # Low clubhouse: patched masonry, mismatched extension and corrugated shallow roof.
 m.box((3000,-30,-1500),(5000,570,500),brick);m.box((4900,-30,-1300),(5800,390,500),stone)
 roof(m,4000,570,-500,1060,1080,160,metal);roof(m,5350,390,-400,520,950,80,roofmat)
 for z in [-1100,-200]:m.box((2985,160,z-150),(3000,410,z+150),metal)
 m.box((2980,0,-650),(3000,430,-350),wood)
 sig=m.material(sign_texture('cx43_club','LKS KRZYWA PROSTA',(224,214,180),(34,67,44)))
 m.face([(2980,510,-1300),(2980,510,300),(2980,660,300),(2980,660,-1300)],sig)
 # Rusty two dugouts and mismatched simple benches.
 for z in [-2100,1700]:
  x=-3000;m.box((x-180,-30,z-520),(x+180,320,z+520),metal);m.box((x+170,15,z-460),(x+185,275,z+460),wood);roof(m,x,320,z,230,570,50,metal)
  m.box((x-110,0,z-440),(x+160,30,z+440),stone)
 for side in [-1,1]:
  for j in range(8):
   x=side*(2900+(j%2)*250);z=-3600+j*900;angle=rng.uniform(-.15,.15)
   rotated_box(m,(-90,75,-280),(90,105,280),x,z,angle,wood)
   for zz in [-200,200]:rotated_box(m,(-65,-20,zz-25),(65,75,zz+25),x,z,angle,metal)
 for j,(text,color) in enumerate([('B KLASA',(40,72,47)),('WULKANIZACJA',(142,91,35)),('KIELBASA + HERBATA',(113,46,38))]):
  mat=m.material(sign_texture('cx43_sign'+str(j),text,(211,201,169),color));x=-1050+j*1050;z=-3900
  for dx in [-420,420]:m.rod((x+dx,-20,z),(x+dx,330,z),12,metal)
  m.face([(x-470,150,z),(x+470,150,z),(x+470,390,z),(x-470,390,z)],mat)
 for j in range(18):tree(m,rng.choice([-1,1])*rng.uniform(5200,6500),rng.uniform(-6300,6300),rng.uniform(450,900),wood,leaf,rng,'oak')
 m.mark('crooked_chain_link_fence_rusty_dugouts_patched_clubhouse');m.mark('fictional_B_klasa_signs_mismatched_benches');return m

def export(m,path,check_exclusion=True):
 assert len(m.v)<65535,(m.name,len(m.v));assert 0<len(m.materials)<=32,(m.name,len(m.materials));assert len(m.uv)==len(m.v)
 out=bytearray(TEMPLATE[:5344]);struct.pack_into('<II',out,8,1,1)
 for j,texture in enumerate(m.materials):
  out[16+j*164:16+(j+1)*164]=TEMPLATE[16:180];out[16+j*164:48+j*164]=texture.encode('ascii').ljust(32,b'\0')
 nv,nf=len(m.v),len(m.f);struct.pack_into('<III',out,5264,len(m.materials),nf,nv);bounds=[min(v[k] for v in m.v) for k in range(3)]+[max(v[k] for v in m.v) for k in range(3)];struct.pack_into('<6f',out,5280,*bounds)
 block=bytearray(156);struct.pack_into('<I',block,0,1);block[4:36]=m.name.encode().ljust(32,b'\0');struct.pack_into('<11I',block,36,nv,nf,0,nf,0,0,0,nv,0,0,2);struct.pack_into('<6f',block,80,*bounds);struct.pack_into('<hH',block,104,-1,0)
 def stream(pointer,data):struct.pack_into('<I',block,pointer,5344+len(block));block.extend(data)
 flat=[i for f in m.f for i in f]
 for pointer,data in [(124,struct.pack('<'+'H'*len(flat),*flat)),(128,struct.pack('<'+'H'*nf,*m.mi)),(132,struct.pack('<'+'H'*len(flat),*flat)),(136,struct.pack('<'+'f'*(nv*2),*(x for u,v in m.uv for x in (u,1-v)))),(140,struct.pack('<'+'f'*(nv*3),*(x for p in m.v for x in p))),(144,struct.pack('<'+'f'*(nv*3),*(x for n in m.n for x in n)))]:stream(pointer,data)
 for pointer,val in [(108,(0,0,0)),(112,(0,0,0,1)),(116,(1,1,1))]:
  t=5344+len(block);stream(pointer,struct.pack('<4I',0,1,3,t+16+4*len(val))+struct.pack('<'+'f'*len(val),*val)+struct.pack('<I',0)+struct.pack('<'+'f'*len(val),*val))
 struct.pack_into('<I',block,152,len(block));path.write_bytes(out+block);check=inspect(path);assert check['end']==len(out+block)
 # Triangle AABBs must never overlap the playable exclusion rectangle.
 bad=[]
 for j,f in enumerate(m.f):
  v=[m.v[i] for i in f];xx=[p[0] for p in v];zz=[p[2] for p in v]
  if max(xx)>-1900 and min(xx)<1900 and max(zz)>-3300 and min(zz)<3300:bad.append(j)
 if check_exclusion:assert not bad,(m.name,'pitch overlap',bad[:10])
 return dict(native_mesh='Data/Meshes/Objects/'+path.name,bounds=bounds,vertices=nv,triangles=nf,materials=m.materials,features=m.features,exclusion_overlaps=0)

def map_assets(ident,folder,palette):
 target=D/'Levels'/folder;target.mkdir(parents=True,exist_ok=True);b=(SRC/'Niedzwiedzie.map').read_bytes();sub={b'Niedzwiedzie':folder.encode(),b'B_Zima':f'D{ident}tex'.encode(),b'NieboZorza':f'Sky{ident}Frame'.encode()}
 # Neutral low stones/grass replace snow-specific objects; actual architecture is the backdrop.
 for j,old in enumerate(['iglo','balwan','choinkaZima1','choinkaZima2','choinkaBombki','zaspa','sanki']):
  name=(f'P{ident}'+chr(65+j)).ljust(len(old),'0');sub[old.encode()]=name.encode();m=Mesh(name);m.material(texture('cx'+str(ident)+'_neutral','stone',palette,ident))
  if j in [0,1,5,6]:m.loft([(0,-30,0,100,80),(0,15,0,110,70),(0,35,0,40,30)],0,7)
  else:m.box((-8,-10,-8),(8,6,8),0)
  export(m,D/'Meshes/Objects'/(name+'.3da'),False)
 for a,v in sub.items():assert len(a)==len(v);b=re.sub(re.escape(a),v,b,flags=re.I)
 assert len(b)==80029;(target/(folder+'.map')).write_bytes(b)
 for kind in ['H','S']:shutil.copy2(SRC/f'PS_{kind}_Niedzwiedzie.png',target/f'PS_{kind}_{folder}.png')
 Image.new('RGBA',(32,32),(0,0,0,0)).save(target/f'PS_D_{folder}_Drzewa.png')
 # Recolor only surface appearance; exact inherited pitch outline stays aligned.
 rng=random.Random(ident);outside=palette;field={'38':(94,110,66),'39':(66,106,74),'40':(85,106,84),'41':(102,153,62),'42':(61,99,72),'43':(96,116,59)}[str(ident)]
 im=Image.new('RGB',(1024,1024),outside);px=im.load()
 for y in range(1024):
  for x in range(1024):
   n=rng.randrange(-8,9);c=field if 392<=x<=632 and 304<=y<=720 else outside;px[x,y]=tuple(max(0,min(255,v+n)) for v in c)
 d=ImageDraw.Draw(im)
 if ident==41:
  for y in range(0,1024,24):
   for x in range(0,1024,24):
    if 380<x<650 and 285<y<740:continue
    c=tuple(max(0,min(255,v+rng.randrange(-15,16))) for v in outside);d.rectangle((x,y,x+23,y+23),fill=c)
 if ident==43:
  for j in range(70):
   x=rng.choice([rng.randrange(290,390),rng.randrange(640,760)]);y=rng.randrange(250,770);d.ellipse((x,y,x+rng.randrange(5,30),y+rng.randrange(5,30)),fill=(96,81,52))
 line=(228,225,201);d.rectangle((403,315,621,710),outline=line,width=2);d.line((403,513,621,513),fill=line,width=2);d.ellipse((474,475,551,552),outline=line,width=2);d.rectangle((464,315,561,373),outline=line,width=2);d.rectangle((464,652,561,710),outline=line,width=2)
 im.save(target/f'PS_C_{folder}.png');Image.new('RGB',(1,1),outside).save(target/f'PS_C_{folder}_horizon.png')
 detail=D/'Textures/Detail';detail.mkdir(exist_ok=True);di=Image.new('RGB',(128,128));di.putdata([(v,v,v) for v in (rng.randrange(176,185) for _ in range(16384))]);di.save(detail/f'D{ident}tex.png')
 skyroot=D/'Meshes/Sky';skyroot.mkdir(exist_ok=True);sky=bytearray((BASE/'Data/Meshes/Sky/NieboZorza.3DA').read_bytes());sky[16:48]=f'CXsky{ident}.png'.encode().ljust(32,b'\0');(skyroot/f'Sky{ident}Frame.3da').write_bytes(sky);shutil.copy2(BASE/'Data/Meshes/Sky/NieboZorza.mat',skyroot/f'Sky{ident}Frame.mat')
 si=Image.new('RGB',(512,256));sd=ImageDraw.Draw(si);top=(55,97,131) if ident!=40 else (74,91,103);bottom=(184,194,184) if ident!=40 else (168,177,174)
 for y in range(256):sd.line((0,y,511,y),fill=tuple(round(a+(v-a)*y/255) for a,v in zip(top,bottom)))
 si.save(D/'Textures'/f'CXsky{ident}.png')
 return dict(folder=folder,level_path=f'Data/Levels/{folder}/{folder}.map',base_map_bytes_preserved=len(b),base_gameplay_coordinates_unchanged=True)

if __name__=='__main__':
 entries=[(38,'OldCampArena','Stary Oboz',build_gothic,(111,100,73)),(39,'SummonerRift','Summoner\'s Rift',build_rift,(72,104,74)),(40,'KaerMorhen__','Kaer Morhen',build_kaer,(109,116,108)),(41,'PlainsBiome_','Minecraft: Plains',build_minecraft,(107,146,62)),(42,'SejmArena___','Sejm',build_sejm,(136,125,103)),(43,'BKlasaArena_','B Klasa',build_bklasa,(112,108,79))]
 result=[]
 for ident,folder,name,builder,palette in entries:
  assert len(folder)==12,(folder,len(folder));m=builder();rec=export(m,D/'Meshes/Objects'/f'CXarena{ident}.3da');rec.update(map_id=ident,name=name,backdrop_position=CENTER,backdrop_rotation=[0,0,0],backdrop_scale=1,collision=False,footprint_exclusion=EXCLUSION);rec.update(map_assets(ident,folder,palette));result.append(rec);print('BUILT',ident,name,rec['triangles'],rec['vertices'],len(rec['materials']),flush=True)
 (O/'arenas-manifest.json').write_text(json.dumps(result,indent=2));print('ALL SIX ARENAS BUILT',flush=True)
