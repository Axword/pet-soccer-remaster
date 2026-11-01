"""Second source/style pass after independent review. Own task staging only."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,math,json,random,collections,struct
O=pathlib.Path(__file__).parent;sys.path.insert(0,str(O));from build_arenas import *

def placed_box(m,lo,hi,x,z,a,mat):
 co,si=math.cos(a),math.sin(a);aa,bb,cc=lo;xx,yy,zz=hi
 def t(p):return (p[0]*co+p[2]*si+x,p[1],-p[0]*si+p[2]*co+z)
 for f in [[(aa,yy,cc),(xx,yy,cc),(xx,bb,cc),(aa,bb,cc)],[(xx,yy,zz),(aa,yy,zz),(aa,bb,zz),(xx,bb,zz)],[(aa,yy,zz),(aa,yy,cc),(aa,bb,cc),(aa,bb,zz)],[(xx,yy,cc),(xx,yy,zz),(xx,bb,zz),(xx,bb,cc)],[(aa,yy,zz),(xx,yy,zz),(xx,yy,cc),(aa,yy,cc)],[(aa,bb,cc),(xx,bb,cc),(xx,bb,zz),(aa,bb,zz)]]:m.face([t(p) for p in f],mat)

class ArtMesh(Mesh):
 def __init__(self,name):super().__init__(name);self.repeat={}
 def face(self,p,mat=0,uv=None):
  if uv is None and mat in self.repeat:
   a,b,c=[Vector(v) for v in p[:3]];n=(b-a).cross(c-a);k=max(range(3),key=lambda j:abs(n[j]));axes={0:(2,1),1:(0,2),2:(0,1)}[k];s=self.repeat[mat];uv=[(v[axes[0]]/s,v[axes[1]]/s) for v in p]
  return super().face(p,mat,uv)

def art_texture(name,kind,base,seed):
 rng=random.Random(seed);size=512;im=Image.new('RGB',(size,size));pix=im.load()
 for y in range(size):
  for x in range(size):
   n=rng.randrange(-9,10)+int(9*math.sin(x*.017+y*.008)*math.cos(y*.021));pix[x,y]=tuple(max(0,min(255,v+n)) for v in base)
 d=ImageDraw.Draw(im)
 if kind=='weatherstone':
  y=0
  while y<size:
   h=rng.randrange(17,32);x=-rng.randrange(5,60)
   while x<size:
    w=rng.randrange(28,74);n=rng.randrange(-17,18);c=tuple(max(0,min(255,v+n)) for v in base)
    p=[(x+2,y+2),(x+w-4,y+1),(x+w-2,y+h-3),(x+3,y+h-1)];d.polygon(p,fill=c,outline=tuple(int(v*.63) for v in c));d.line([p[0],p[1]],fill=tuple(min(255,int(v*1.13)) for v in c),width=2)
    if rng.random()<.18:d.line((x+w*.3,y+2,x+w*.38,y+h*.5,x+w*.3,y+h-2),fill=tuple(int(v*.55) for v in c),width=1)
    x+=w
   y+=h
  for _ in range(60):
   x,y=rng.randrange(size),rng.randrange(size);r=rng.randrange(3,25);d.ellipse((x,y,x+r,y+r*2),fill=tuple(int(v*.7) for v in base))
 elif kind=='paintedrock':
  for j in range(14):
   y=rng.randrange(size);pts=[(-30,y),(100,y+rng.randrange(-25,26)),(270,y+rng.randrange(-25,26)),(540,y+rng.randrange(-30,31))];d.line(pts,fill=tuple(int(v*.72) for v in base),width=rng.randrange(3,9));d.line([(x,y-4) for x,y in pts],fill=tuple(min(255,int(v*1.2)) for v in base),width=3)
 elif kind=='bark':
  for j in range(36):
   x=rng.randrange(size);d.line([(x,-20),(x+rng.randrange(-20,21),160),(x+rng.randrange(-15,16),350),(x,540)],fill=tuple(int(v*.55) for v in base),width=rng.randrange(2,7));d.line((x+6,0,x+14,512),fill=tuple(min(255,int(v*1.18)) for v in base),width=2)
 elif kind=='leafpaint':
  for j in range(130):
   x,y=rng.randrange(size),rng.randrange(size);w,h=rng.randrange(15,70),rng.randrange(8,35);n=rng.randrange(-22,23);d.polygon([(x-w,y),(x,y-h),(x+w,y+h*.2),(x,y+h)],fill=tuple(max(0,min(255,v+n)) for v in base))
 elif kind=='slate':
  for y in range(0,size,20):
   for x in range(-40,size,35):
    n=rng.randrange(-18,19);xx=x+(17 if y//20%2 else 0);d.polygon([(xx,y+1),(xx+32,y),(xx+31,y+18),(xx+2,y+19)],fill=tuple(max(0,min(255,v+n)) for v in base),outline=tuple(int(v*.5) for v in base))
 im.save(D/'Textures'/(name+'.png'));return name+'.png'

def tube(m,path,radii,mat,sides=7):
 path=[Vector(p) for p in path];rings=[]
 for j,p in enumerate(path):
  tangent=(path[min(j+1,len(path)-1)]-path[max(0,j-1)]).normalized();right=tangent.cross(Vector((0,1,0)))
  if right.length<.01:right=tangent.cross(Vector((1,0,0)))
  right.normalize();up=tangent.cross(right);r=radii[j];rings.append([p+r*(right*math.cos(i*math.tau/sides)+up*math.sin(i*math.tau/sides)) for i in range(sides)])
 for a,b in zip(rings,rings[1:]):
  for j in range(sides):m.face([a[j],b[j],b[(j+1)%sides],a[(j+1)%sides]],mat)
 m.face(rings[0][::-1],mat,[(0,0)]*sides);m.face(rings[-1],mat,[(0,0)]*sides)

def jagged_rock(m,x,z,rx,rz,h,side,top,rng,y0=-50):
 # Unequal facet rings, sheared summit and a broad diagonal ledge, not a radial cone.
 sides=7;angles=[j*math.tau/sides+rng.uniform(-.12,.12) for j in range(sides)];radii=[rng.uniform(.78,1.2) for _ in range(sides)];rings=[]
 for j,(yy,r,shear) in enumerate([(y0,1,0),(h*.27,1.08,-.08),(h*.72,.83,.2),(h,.38,.35)]):
  rings.append([(x+math.cos(a)*rx*rr*r+rx*shear,yy+rng.uniform(-.05,.05)*h,z+math.sin(a)*rz*rr*r-rz*shear*.3) for a,rr in zip(angles,radii)])
 for k,(a,b) in enumerate(zip(rings,rings[1:])):
  for j in range(sides):m.face([a[j],b[j],b[(j+1)%sides],a[(j+1)%sides]],top if k==2 and j%3==0 else side)
 m.face(rings[-1][::-1],top,[(0,0)]*sides)

def foliage_mass(m,x,y,z,rx,ry,rz,mat,rng):
 sides=9;angles=[j*math.tau/sides for j in range(sides)];jitter=[rng.uniform(.78,1.16) for _ in angles];rings=[]
 for yy,r,shift in [(-.7,.45,-.1),(-.35,1,-.05),(.2,1.0,.15),(.65,.68,.25),(.9,.24,.12)]:
  rings.append([(x+math.cos(a)*rx*j*r+shift*rx,y+yy*ry+rng.uniform(-.04,.04)*ry,z+math.sin(a)*rz*j*r) for a,j in zip(angles,jitter)])
 for a,b in zip(rings,rings[1:]):
  for j in range(sides):m.face([a[j],b[j],b[(j+1)%sides],a[(j+1)%sides]],mat)
 m.face(rings[-1][::-1],mat,[(.5,.5)]*sides)

def organic_tree(m,x,z,h,wood,leaf,light,rng,evergreen=False):
 drift=rng.uniform(-.15,.15)*h;path=[(x,-45,z),(x-drift*.2,h*.25,z),(x+drift*.35,h*.57,z+h*.04),(x+drift,h*.85,z-h*.03)]
 tube(m,path,[h*.12,h*.10,h*.075,h*.03],wood)
 for j in range(5):
  a=j*math.tau/5+rng.uniform(-.2,.2);end=(x+math.cos(a)*h*.5,5,z+math.sin(a)*h*.5);tube(m,[end,(x+math.cos(a)*h*.24,h*.14,z+math.sin(a)*h*.24),(x,h*.31,z)],[h*.018,h*.07,h*.10],wood)
 if evergreen:
  for j in range(4):
   yy=h*(.44+j*.17);rr=h*(.31-j*.05);foliage_mass(m,x+drift*(j+1)/5,yy,z,rr,h*.25,rr,leaf if j<2 else light,rng)
 else:
  for dx,yy,dz,r in [(-.25,.74,0,.44),(.20,.88,.11,.43),(.04,1.02,-.16,.34)]:
   branch=(x+dx*h,yy*h,z+dz*h);tube(m,[(x,h*.48,z),branch],[h*.065,h*.025],wood);foliage_mass(m,*branch,h*r,h*.31,h*r,leaf if yy<.9 else light,rng)

def build_rift_v2():
 m=ArtMesh('CXarena39');rng=random.Random(3902)
 stone=m.material(art_texture('cx39v2_stone','paintedrock',(110,127,120),1));top=m.material(art_texture('cx39v2_top','paintedrock',(141,151,128),2));wood=m.material(art_texture('cx39v2_bark','bark',(102,76,46),3));leaf=m.material(art_texture('cx39v2_leaf','leafpaint',(37,82,61),4));light=m.material(art_texture('cx39v2_light','leafpaint',(55,108,72),5));gold=m.material(art_texture('cx39v2_gold','paintedrock',(139,126,77),6));water=m.material(art_texture('cx39v2_water','paintedrock',(40,103,129),7));waterlight=m.material(art_texture('cx39v2_wave','paintedrock',(63,142,157),8));moss=m.material(art_texture('cx39v2_moss','leafpaint',(66,99,58),9))
 blue=m.material(texture('cx39_blue','plain',(43,161,218),91));red=m.material(texture('cx39_red','plain',(191,62,87),92));dark=m.material(art_texture('cx39v2_dark','paintedrock',(53,71,69),10))
 m.repeat={stone:900,top:900,wood:800,moss:900,gold:800,dark:850}
 # Opposing recognizable Nexus platforms, with layered carved rims and root-like braces.
 for z,magic in [(-4650,blue),(4650,red)]:
  m.loft([(0,-40,z,1050,730),(0,60,z,1050,730),(0,135,z,900,620),(0,185,z,800,540)],stone,16)
  for j in range(16):
   a=j*math.tau/16;x=math.cos(a)*880;zz=z+math.sin(a)*600;m.rod((x,120,zz),(x*.88,190,z+(zz-z)*.88),28,gold,5)
  m.loft([(0,180,z,400,285),(0,290,z,330,240)],gold,10);crystal(m,0,z,270,270,980,magic)
  for j in range(4):
   a=j*math.tau/4+math.pi/4;x=math.cos(a)*460;zz=z+math.sin(a)*320;tube(m,[(x*1.45,160,z+(zz-z)*1.45),(x*1.12,420,z+(zz-z)*1.12),(x*.65,550,z+(zz-z)*.65)],[85,68,40],stone);crystal(m,x,zz,160,70,330,magic)
 # Guardians have broad shoulders, diagonal stone buttresses and engraved chest plates.
 for x,z,magic in [(-2300,-2750,blue),(2300,-2750,blue),(-2300,2750,red),(2300,2750,red)]:
  m.loft([(x,-30,z,265,265),(x,120,z,265,265),(x,190,z,210,210),(x,620,z,110,115)],stone,8)
  for side in [-1,1]:tube(m,[(x+side*230,150,z+15),(x+side*235,550,z),(x+side*120,800,z-25)],[75,68,48],stone)
  m.box((x-100,350,z-155),(x+100,650,z-125),gold);m.loft([(x,620,z,190,160),(x,725,z,140,130)],top,8);crystal(m,x,z,740,105,300,magic)
 # A continuous visibly raised water ribbon meanders outside the football rectangle.
 centres=[(-3140+260*math.sin(j*.42),190,-5400+j*300) for j in range(37)]
 for j,(a,b) in enumerate(zip(centres,centres[1:])):
  ax,yy,az=a;bx,_,bz=b;w=330+35*math.sin(j*.4)
  m.face([(ax-w,yy,az),(bx-w,yy,bz),(bx+w,yy,bz),(ax+w,yy,az)],water)
  for side in [-1,1]:
   xx0=ax+side*w;xx1=bx+side*w;m.face([(xx0,yy,az),(xx1,yy,bz),(xx1+side*150,yy+75,bz),(xx0+side*150,yy+75,az)],moss)
   outer=[(xx0+side*150,-55,az),(xx1+side*150,-55,bz),(xx1+side*150,yy+75,bz),(xx0+side*150,yy+75,az)];m.face(outer if side>0 else outer[::-1],dark)
  if j%2==0:m.face([(ax-w*.65,yy+1,az+50),(bx-w*.55,yy+1,bz),(bx-w*.45,yy+1,bz+5),(ax-w*.55,yy+1,az+55)],waterlight)
 for point in [centres[0],centres[-1]]:
  x,y,z=point;m.face([(x-480,-55,z),(x+480,-55,z),(x+480,y+75,z),(x-480,y+75,z)],dark)
 # Four curved jungle camps occupy pockets outside sidelines instead of straight barriers.
 for side in [-1,1]:
  for cz in [-1700,1800]:
   cx=side*(4400 if side<0 else 3400)
   for j in range(7):
    a=math.radians(25+j*45);x=cx+math.cos(a)*650;z=cz+math.sin(a)*950;jagged_rock(m,x,z,240,330,350+rng.randrange(300),stone,top,rng)
   for j in range(3):
    x=cx+side*(250+j*210);z=cz-450+j*420;organic_tree(m,x,z,900+rng.randrange(350),wood,leaf,light,rng,j==2)
   for j in range(3):
    z=cz-850+j*650;x=cx+side*450;tube(m,[(x-side*500,30,z-200),(x-side*190,330,z),(x+side*170,480,z+180),(x+side*430,50,z+350)],[35,110,135,45],wood)
 for side in [-1,1]:
  for j in range(7):
   z=-4700+j*1500;x=side*(5300+rng.randrange(700));organic_tree(m,x,z,1100+rng.randrange(450),wood,leaf,light,rng,True)
 for x,z in [(-2700,-5800),(2900,-5700),(-3000,5800),(2800,5900)]:jagged_rock(m,x,z,650,500,1150,stone,top,rng)
 m.mark('SRv2_organic_jungle_camps_buttress_roots_nonconical_canopies');m.mark('continuous_meandering_side_river',surface_y=190,segments=36);m.mark('opposing_Nexus_and_guardian_turrets');return m

def weather_wall(m,a,b,height,thick,mat,rng,base=0,broken=False):
 x0,z0=a;x1,z1=b;length=math.hypot(x1-x0,z1-z0);angle=math.atan2(x1-x0,z1-z0);steps=max(1,int(length/260));dx=(x1-x0)/steps;dz=(z1-z0)/steps
 for j in range(steps):
  h=height+(rng.randrange(-170,45) if broken and j>steps//2 else rng.randrange(-25,26));x=x0+(j+.5)*dx;z=z0+(j+.5)*dz
  placed_box(m,(-thick/2,base,-length/steps/2),(thick/2,h,length/steps/2),x,z,angle,mat)
  if j%2==0 and not(broken and j>steps//2+1):placed_box(m,(-thick*.72,h,-50),(thick*.72,h+95,50),x,z,angle,mat)

def blunt_tower(m,x,z,r,h,stone,dark,rng,base=0,breach=False):
 sides=14;angles=[j*math.tau/sides for j in range(sides)];heights=[h+rng.randrange(-45,46) for _ in angles]
 if breach:
  for j in [2,3,4]:heights[j]-=150+(j%2)*100
 for j,a in enumerate(angles):
  b=angles[(j+1)%sides];p=(x+math.cos(a)*r,base,z+math.sin(a)*r);q=(x+math.cos(b)*r,base,z+math.sin(b)*r);ph=(p[0],heights[j],p[2]);qh=(q[0],heights[(j+1)%sides],q[2]);m.face([p,ph,qh,q],stone)
  # Thick visible parapet encloses a dark recessed top, not a cone roof.
  pi=(x+math.cos(a)*(r-75),heights[j],z+math.sin(a)*(r-75));qi=(x+math.cos(b)*(r-75),heights[(j+1)%sides],z+math.sin(b)*(r-75));m.face([ph,pi,qi,qh],stone);m.face([pi,(pi[0],h-180,pi[2]),(qi[0],h-180,qi[2]),qi],dark)
  if j%2==0 and not(breach and j in [2,4]):placed_box(m,(-55,heights[j],-45),(55,heights[j]+95,45),ph[0],ph[2],-a,stone)
 m.face([(x+math.cos(a)*(r-75),h-185,z+math.sin(a)*(r-75)) for a in angles],dark,[(0,0)]*sides)

def mountain_ridge(m,x,z,width,depth,height,stone,light,rng):
 # Elongated fractured cliff, not a radial pile: eight unequal peaks and vertical strata.
 path=[]
 for j in range(9):path.append((x-width/2+j*width/8,height*(.6+rng.random()*.4),z+rng.uniform(-depth*.3,depth*.3)))
 for a,b in zip(path,path[1:]):
  m.face([(a[0]-160,-70,z-depth),(a[0],a[1],a[2]),(b[0],b[1],b[2]),(b[0]+160,-70,z-depth)],stone)
  m.face([(a[0],a[1],a[2]),(a[0]-width*.025,a[1]*.45,z+depth*.5),(b[0]+width*.025,b[1]*.45,z+depth*.5),(b[0],b[1],b[2])],light)
  m.face([(a[0]-width*.025,a[1]*.45,z+depth*.5),(a[0]-200,-80,z+depth),(b[0]+200,-80,z+depth),(b[0]+width*.025,b[1]*.45,z+depth*.5)],stone)
 for end in [0,-1]:
  a=path[end];q=[(a[0]-160,-70,z-depth),a,(a[0]-width*.025,a[1]*.45,z+depth*.5),(a[0]-200,-80,z+depth)];m.face(q if end==0 else q[::-1],stone)

def build_kaer_v2():
 m=ArtMesh('CXarena40');rng=random.Random(4002)
 stone=m.material(art_texture('cx40v2_stone','weatherstone',(143,137,119),41));dirty=m.material(art_texture('cx40v2_dirty','weatherstone',(109,112,99),42));rockmat=m.material(art_texture('cx40v2_cliff','paintedrock',(119,119,112),43));rocktop=m.material(art_texture('cx40v2_clifftop','paintedrock',(148,146,133),44));wood=m.material(art_texture('cx40v2_wood','bark',(77,62,44),45));leaf=m.material(art_texture('cx40v2_leaf','leafpaint',(35,59,48),46));light=m.material(art_texture('cx40v2_leaflit','leafpaint',(48,77,57),47));dark=m.material(art_texture('cx40v2_dark','weatherstone',(54,61,61),48));slate=m.material(art_texture('cx40v2_slate','slate',(76,79,83),49));m.repeat={stone:650,dirty:650,rockmat:1100,rocktop:1100,wood:700,dark:650,slate:550}
 # A natural escarpment under the WHOLE architectural footprint grounds every wall.
 for x,z,rx,rz,h in [(4500,-800,1600,1800,1000),(4700,1500,1450,1200,950),(3400,200,1000,1700,550)]:jagged_rock(m,x,z,rx,rz,h,rockmat,rocktop,rng)
 # Flat enclosed retaining plinth is hidden behind the irregular cliff face; no hovering keep.
 m.box((3150,-70,-2600),(6400,760,2500),rockmat)
 base=720
 # The unmistakable tall rectangular Kaer Morhen keep with engaged narrow vertical turrets.
 m.box((4300,base,-1550),(5700,base+2700,700),stone)
 m.box((4370,base+2700,-1470),(5630,base+2860,620),dirty)
 for x,z,r,h in [(4300,-1550,165,base+3130),(4300,700,180,base+3060),(5700,-1550,175,base+2890)]:blunt_tower(m,x,z,r,h,stone,dark,rng,base)
 # Broken stepped crown: several surviving high fragments, incomplete central roof timbers.
 for z,h in [(-1300,3600),(-800,3410),(-250,3500),(350,3300)]:m.box((4290,base+2640,z-80),(4380,h,z+80),stone)
 for z in [-1200,-650,-100,450]:
  m.box((4280,base+1100,z-30),(4300,base+1390,z+30),dark);m.box((4280,base+2010,z-27),(4300,base+2280,z+27),dark)
  # Narrow structural buttress, continuous to foundation.
  m.box((4200,base,z-80),(4300,base+2570,z+80),dirty)
 # Lower great hall is ruined and asymmetric, with partial roof and exposed rafters.
 weather_wall(m,(3350,-1600),(3350,1800),base+1350,155,stone,rng,base,True)
 weather_wall(m,(3350,-1600),(4300,-1600),base+1410,160,stone,rng,base,False)
 weather_wall(m,(3350,1800),(4650,1800),base+1050,160,stone,rng,base,True)
 # A short surviving slate roof fragment; most of the hall remains open and broken.
 roof(m,3850,base+1200,-950,500,600,550,slate)
 for z in [-100,450,1000,1550]:
  tube(m,[(3400,base+1140,z),(3850,base+1650,z),(4300,base+1140,z)],[24,24,24],wood,5)
  m.rod((3400,base+1140,z),(4300,base+1140,z),19,wood,5)
 # Nested ramparts step down the cliff; nonmatching heights and breaches carry the silhouette.
 for x0,z0,x1,z1,h,broken in [(2650,-2850,5600,-2850,1050,False),(2650,2850,5600,2850,900,True),(2650,-2850,2650,-850,900,False),(2650,850,2650,2850,800,True),(3000,-1900,3000,2000,1250,True)]:weather_wall(m,(x0,z0),(x1,z1),h,150,stone,rng,0,broken)
 for x,z,r,h,breach in [(2650,-2850,340,1180,False),(2650,2850,390,970,True),(3000,-1900,300,1710,True),(5550,2850,290,1350,True)]:blunt_tower(m,x,z,r,h,stone,dark,rng,0,breach)
 # Roofless front gate: two unequal flanking towers and a masonry arch lintel.
 for z,h in [(-620,940),(620,1120)]:blunt_tower(m,2600,z,245,h,stone,dark,rng,0,True)
 # Rounded source-style gateway: a real thick voussoir ring, not a flat lintel.
 for side in [-1,1]:m.box((2510,0,side*500-55),(2690,500,side*500+55),stone)
 for j in range(12):
  a=j*math.pi/12;b=(j+1)*math.pi/12
  inner=[(math.sin(t)*350+500,math.cos(t)*445) for t in [a,b]];outer=[(math.sin(t)*450+500,math.cos(t)*550) for t in [a,b]]
  for x,reverse in [(2505,True),(2695,False)]:
   q=[(x,inner[0][0],inner[0][1]),(x,inner[1][0],inner[1][1]),(x,outer[1][0],outer[1][1]),(x,outer[0][0],outer[0][1])];m.face(q[::-1] if reverse else q,stone)
  m.face([(2505,inner[0][0],inner[0][1]),(2695,inner[0][0],inner[0][1]),(2695,inner[1][0],inner[1][1]),(2505,inner[1][0],inner[1][1])],stone)
 # Chipped wall rubble and long wooden gallery/scaffold attached to the hall.
 for j in range(20):jagged_rock(m,3100+rng.randrange(600),1650+rng.randrange(700),rng.randrange(50,130),rng.randrange(50,120),rng.randrange(50,180),dirty,stone,rng,y0=-10)
 for z in [-1300,-650,0,650]:
  m.box((3190,base+430,z-270),(3380,base+475,z+270),wood);m.rod((3200,base+430,z),(3340,base+80,z),20,wood);m.rod((3190,base+470,z),(3190,base+650,z),14,wood)
 for z in [-1400,-400,600,1600]:m.rod((3190,base+645,z),(3190,base+645,z+800),14,wood)
 # The keep nestles against a jagged wall of mountains, not isolated rounded rocks.
 start=len(m.v);mountain_ridge(m,0,0,6000,900,4900,rockmat,rocktop,rng);m.transformed(lambda p:(6200+p.z,p.y,p.x),start)
 mountain_ridge(m,-5200,-6300,4500,1300,2400,rockmat,rocktop,rng)
 for side in [-1,1]:
  for j in range(14):
   x=side*rng.uniform(4000,6400);z=rng.uniform(-6200,6200)
   if side==1 and -3300<z<3300:continue
   organic_tree(m,x,z,rng.uniform(650,1150),wood,leaf,light,rng,True)
 m.mark('KMv2_tall_rectangular_keep_engaged_turrets_asymmetric_broken_great_hall');m.mark('nested_roofless_breached_ramparts_grounded_cliff_foundation');m.mark('weathered_small_course_stone_and_jagged_mountain_backwall');return m

def build_sejm_v2():
 m=ArtMesh('CXarena42');stone,wood,green,leaf,gold,metal,cream=mats(m,42,'sejm');m.repeat={wood:700,stone:900};seats=0
 floor=m.material(art_texture('cx42v2_floor','weatherstone',(166,154,126),4242));m.repeat[floor]=1000
 # A continuous elliptical horseshoe is outside the rectangle; terraces support every row.
 amin,amax=math.radians(125),math.radians(415)
 for row in range(5):
  rx=3800+row*340;rz=5350+row*260;y=row*95;irx=rx-320;irz=rz-300;orx=rx+320;orz=rz+300
  for j in range(62):
   a=amin+(amax-amin)*j/62;b=amin+(amax-amin)*(j+1)/62
   q=[(math.cos(a)*irx,y,math.sin(a)*irz),(math.cos(b)*irx,y,math.sin(b)*irz),(math.cos(b)*orx,y,math.sin(b)*orz),(math.cos(a)*orx,y,math.sin(a)*orz)]
   m.face(q,floor)
   # Fully grounded vertical riser/base, including the inner and outer edges.
   for k,l in [(1,0),(3,2)]:m.face([(q[k][0],-35,q[k][2]),q[k],q[l],(q[l][0],-35,q[l][2])],wood)
   if j in [0,61]:
    k,l=(0,3) if j==0 else (2,1);m.face([(q[k][0],-35,q[k][2]),q[k],q[l],(q[l][0],-35,q[l][2])],wood)
  for j in range(31):
   a=amin+(amax-amin)*(j+.5)/31;x=rx*math.cos(a);z=rz*math.sin(a);angle=-a+math.pi/2
   placed_box(m,(-110,y,-75),(110,y+190,75),x,z,angle,wood);placed_box(m,(-80,y+95,90),(80,y+115,245),x,z,angle,green);placed_box(m,(-80,y+100,225),(80,y+290,265),x,z,angle,green)
   for xx in [-55,55]:placed_box(m,(xx-13,y,120),(xx+13,y+100,235),x,z,angle,wood)
   seats+=1
 # Presidium at +Z, with prominent all-angle Polish flags above the timber wall.
 m.box((-1700,-35,5250),(1700,220,6600),wood);m.box((-1400,220,5550),(1400,620,6100),wood);m.box((-400,220,5150),(400,760,5500),wood);m.box((-520,740,5090),(520,790,5550),wood)
 m.box((-1900,0,6650),(1900,1800,6780),wood)
 white=m.material(texture('cx42_white','plain',(235,234,217),42));red=m.material(texture('cx42_red','plain',(179,40,49),43))
 for x in [-1650,1300]:
  m.rod((x,0,6450),(x,3250,6450),14,metal)
  for a,b,mat in [(3100,2650,white),(2650,2200,red)]:
   m.box((x,b,6447),(x+650,a,6453),mat)
 # Front and back have white-red national panels; they remain visible in all review angles.
 for z in [6640,6790]:
  for y0,y1,mat in [(1100,1500,white),(700,1100,red)]:m.box((-520,y0,z-2),(520,y1,z+2),mat)
 for x in [-6350,6350]:
  for z in range(-5700,5701,950):m.loft([(x,-40,z,130,130),(x,1750,z,110,110)],cream,10);m.box((x-170,1730,z-170),(x+170,1840,z+170),stone)
  m.box((x-180,1820,-6300),(x+180,1990,6300),stone)
 m.mark('Sejmv2_connected_hemicycle_grounded_terraces',seat_count=seats);m.mark('raised_double_sided_Polish_flags_marshal_rostrum_national_panels');return m

def hull(points):
 points=sorted(set(points))
 if len(points)<=2:return points
 def c(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lower=[]
 for p in points:
  while len(lower)>=2 and c(lower[-2],lower[-1],p)<=0:lower.pop()
  lower.append(p)
 upper=[]
 for p in reversed(points):
  while len(upper)>=2 and c(upper[-2],upper[-1],p)<=0:upper.pop()
  upper.append(p)
 return lower[:-1]+upper[:-1]

def close_gothic_exteriors(m):
 s=json.loads((O/'source/oldcamp-source.json').read_text());polys=s['polygons'];used=[s['positions'][i] for _,p,_ in polys for i in p];lo=[min(v[k] for v in used) for k in range(3)];hi=[max(v[k] for v in used) for k in range(3)];mid=[(a+b)/2 for a,b in zip(lo,hi)];factor=.43
 def conv(v):x,y,z=v;return (4700-(z-mid[2])*factor,(y-lo[1])*factor-40,(x-mid[0])*factor+500)
 # Keep actual complete roof silhouettes and genuine door/window details. The old
 # spatial crop contained interior/cut wall faces; those are intentionally omitted.
 names=[]
 for t in s['materials'].values():
  if t not in names:names.append(t)
 wallmat=4+names.index('OCODWATORRANDLOS.TGA');retained=[(f,mi) for f,mi in zip(m.f,m.mi) if mi<4 or mi>=31];m.f=[f for f,_ in retained];m.mi=[mi for _,mi in retained]
 edges=collections.Counter();oriented={};roofvertices=[];source_faces=0
 for mat,ids,features in polys:
  name=s['materials'][str(mat)];isroof='ZIEGEL' in name
  if not (isroof or any(t in name for t in ['FENSTER','TORDOOR','TORBIGDOOR'])):continue
  pts=[conv(s['positions'][i]) for i in ids];uv=[s['features'][i]['uv'] for i in features];mi=4+names.index(name);m.face(pts[::-1],mi,uv[::-1]);source_faces+=1
  if isroof:
   roofvertices.extend(pts);loop=ids[::-1]
   for a,b in zip(loop,loop[1:]+loop[:1]):key=tuple(sorted((a,b)));edges[key]+=1;oriented[key]=(a,b)
 count=0
 for key,n in edges.items():
  if n!=1:continue
  ia,ib=oriented[key];a=conv(s['positions'][ia]);b=conv(s['positions'][ib]);length=math.hypot(b[0]-a[0],b[2]-a[2])
  if length<1:continue
  m.face([a,(a[0],-55,a[2]),(b[0],-55,b[2]),b],wallmat,[(0,a[1]/500),(0,-.11),(length/500,-.11),(length/500,b[1]/500)]);count+=1
 # Join the four source roof spires with their single solid masonry tower body.
 high=[v for v in roofvertices if v[1]>2400]
 if high:
  low=[min(v[k] for v in high) for k in range(3)];upper=[max(v[k] for v in high) for k in range(3)];cx=(low[0]+upper[0])/2;cz=(low[2]+upper[2])/2;rx=(upper[0]-low[0])*.47;rz=(upper[2]-low[2])*.47
  m.loft([(cx,-65,cz,rx*1.22,rz*1.22),(cx,1450,cz,rx,rz),(cx,2400,cz,rx*.83,rz*.83)],wallmat,8)
 m.box((3250,-80,-2050),(6200,65,2400),wallmat)
 # Compact unused vertices from the discarded interior crop, keeping native indices small.
 usedids=sorted({i for f in m.f for i in f});mapping={old:new for new,old in enumerate(usedids)}
 for attr in ['v','n','uv']:setattr(m,attr,[getattr(m,attr)[i] for i in usedids])
 m.f=[tuple(mapping[i] for i in f) for f in m.f]
 m.mark('Gothicv3_actual_roofs_doors_windows_with_closed_grounded_exteriors',grounded_boundary_walls=count,retained_source_faces=source_faces)
 return m

def paint_rift_ground(folder):
 path=D/'Levels'/folder/f'PS_C_{folder}.png';im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im)
 def p(x,z):return ((x+CENTER[0])/15000*1024,(z+CENTER[2])/15000*1024)
 rng=random.Random(3903)
 # Broad dirt lanes and moss-rimmed rock islands outside the preserved central football field.
 for side in [-1,1]:
  pts=[p(side*(2800+400*math.sin(j*.42)),-5500+j*400) for j in range(29)];d.line(pts,fill=(101,101,64),width=34,joint='curve');d.line(pts,fill=(113,107,70),width=19,joint='curve')
 river=[p(-3140+260*math.sin(j*.42),-5400+j*300) for j in range(37)];d.line(river,fill=(42,82,82),width=65,joint='curve');d.line(river,fill=(42,111,133),width=43,joint='curve')
 for side in [-1,1]:
  for cz in [-1700,1800]:
   cx=side*(4400 if side<0 else 3400);x,z=p(cx,cz);d.ellipse((x-40,z-60,x+40,z+60),fill=(67,81,51),outline=(103,113,82),width=8)
 # Restore the exact previous central football surface after painting peripheral lanes.
 previous=Image.open(path).convert('RGB');a=p(-1900,-3300);b=p(1900,3300);rect=(round(a[0]),round(a[1]),round(b[0]),round(b[1]));im.paste(previous.crop(rect),rect);im.save(path)

if __name__=='__main__':
 ids={int(x) for x in sys.argv[sys.argv.index('--')+1:]} if '--' in sys.argv else {38,39,40,42};rows=json.loads((O/'arenas-manifest.json').read_text())
 for row in rows:
  ident=row['map_id']
  if ident not in ids:continue
  m=close_gothic_exteriors(build_gothic()) if ident==38 else {39:build_rift_v2,40:build_kaer_v2,42:build_sejm_v2}[ident]()
  row.update(export(m,D/'Meshes/Objects'/pathlib.Path(row['native_mesh']).name));row['style_revision']=2
  if ident==39:paint_rift_ground(row['folder'])
  print('REFINED',ident,row['triangles'],row['vertices'],flush=True)
 (O/'arenas-manifest.json').write_text(json.dumps(rows,indent=2))
