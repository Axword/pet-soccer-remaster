"""Connected retro character forms; palette atlas and native vertex skin."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,math
from mathutils import Vector
P=pathlib.Path(__file__).parent;sys.path.insert(0,str(P.parent.parent/'tools/python'))
from PIL import Image
from export_skinned_character import export_skin
COLORS=['#d8a17d','#efd0ad','#f2eee1','#211f25','#62402c','#9b673c','#4c3022','#b87b49','#566b83','#283548','#61734d','#a5b8c4','#972f2b','#e1b132','#f1cf37','#304a8a','#ee5942','#65abb7','#c4c3b7','#a49a89','#5a4140','#c88151','#314035','#bfad8c','#623c59','#d1a742','#b9cfd1','#dbe3d9','#1c242a','#663722','#cb9068','#e4baa0']
class Mesh:
 def __init__(self,stem):
  self.stem=stem;self.v=[];self.n=[];self.uv=[];self.f=[];self.w=[]
  pivots=[(0,0,0),(0,25,0),(0,34,0),(0,44,0),(0,46,0),(5,42,0),(9,42,0),(11,31,0),(11,22,0),(-5,42,0),(-9,42,0),(-11,31,0),(-11,22,0),(4,25,0),(4,13,0),(4,3,0),(-4,25,0),(-4,13,0),(-4,3,0)]
  defs=[('Root',0,-1),('Pelvis',2,0),('Spine',3,1),('Neck',40,2),('Head',43,3),('LClav',53,2),('LArm',54,5),('LFore',55,6),('LHand',56,7),('RClav',74,2),('RArm',75,9),('RFore',76,10),('RHand',77,11),('LThigh',4,1),('LCalf',5,13),('LFoot',6,14),('RThigh',22,1),('RCalf',23,16),('RFoot',24,17)]
  self.bones=[dict(name=n,native=b,parent=p,pivot=list(v)) for (n,b,p),v in zip(defs,pivots)]
 def face(self,points,c,bone):
  points=[Vector(p) for p in points];base=len(self.v);normal=(points[1]-points[0]).cross(points[2]-points[0])
  if normal.length<1e-7:return
  normal.normalize();self.v.extend(map(list,points));self.n.extend([list(normal)]*len(points));self.uv.extend([((c%8+.5)/8,1-(c//8+.5)/4)]*len(points));self.w.extend([[(bone,1)]]*len(points))
  for i in range(1,len(points)-1):self.f.append([base,base+i,base+i+1])
 def ell(self,center,size,c,bone,sides=10,rings=6):
  rows=[]
  for j in range(rings+1):
   t=math.pi*(j+.0001)/(rings+.0002);rows.append([(center[0]+size[0]*math.sin(t)*math.cos(i*2*math.pi/sides),center[1]+size[1]*math.cos(t),center[2]+size[2]*math.sin(t)*math.sin(i*2*math.pi/sides)) for i in range(sides)])
  for j in range(rings):
   for i in range(sides):self.face([rows[j][i],rows[j][(i+1)%sides],rows[j+1][(i+1)%sides],rows[j+1][i]],c,bone)
 def loft(self,rows,c,bone,sides=10):
  # row = y, horizontal radius, depth radius, optional center x/z.
  points=[[( (r[3] if len(r)>3 else 0)+r[1]*math.cos(i*2*math.pi/sides),r[0],(r[4] if len(r)>4 else 0)+r[2]*math.sin(i*2*math.pi/sides)) for i in range(sides)] for r in rows]
  for a,b in zip(points,points[1:]):
   for i in range(sides):self.face([a[i],b[i],b[(i+1)%sides],a[(i+1)%sides]],c,bone)
  self.face(points[0],c,bone);self.face(points[-1][::-1],c,bone)
 def box(self,lo,hi,c,bone):
  a,b,d=lo;x,y,z=hi
  for q in [[(a,y,d),(x,y,d),(x,b,d),(a,b,d)],[(x,y,z),(a,y,z),(a,b,z),(x,b,z)],[(a,y,z),(a,y,d),(a,b,d),(a,b,z)],[(x,y,d),(x,y,z),(x,b,z),(x,b,d)],[(a,y,z),(x,y,z),(x,y,d),(a,y,d)],[(a,b,d),(x,b,d),(x,b,z),(a,b,z)]]:self.face(q,c,bone)
 def rod(self,a,b,r,c,bone,sides=8):
  a=Vector(a);b=Vector(b);axis=(b-a).normalized();right=axis.cross(Vector((0,0,1)))
  if right.length<.1:right=axis.cross(Vector((1,0,0)))
  right.normalize();up=axis.cross(right);low=[a+r*(right*math.cos(i*2*math.pi/sides)+up*math.sin(i*2*math.pi/sides)) for i in range(sides)];high=[p+b-a for p in low]
  for i in range(sides):self.face([low[i],high[i],high[(i+1)%sides],low[(i+1)%sides]],c,bone)
  self.face(low,c,bone);self.face(high[::-1],c,bone)
 def face_features(self,center=(0,50,-.5),size=(4.8,6,4.5),skin=0,nose=1.0,mustache=False):
  x,y,z=center;rx,ry,rz=size;self.ell(center,size,skin,4,12,7)
  for side in [-1,1]:
   ex=x+side*rx*.39;ey=y+ry*.12;ez=z-rz*.92
   self.ell((ex,ey,ez),(rx*.22,ry*.13,.4),2,4,8,4);self.ell((ex,ey,ez-.32),(.34,ry*.095,.19),3,4,8,4)
   self.rod((ex-.8,ey+1.0,ez+.1),(ex+.8,ey+1.15,ez+.1),.22,4,4,6)
   self.ell((x+side*rx,y-.2,z),(.65,1.35,.65),skin,4,8,4)
  self.ell((x,y-.65,z-rz+.2),(nose,1.7,nose*.9),skin,4,8,5)
  self.rod((x-1,y-ry*.48,z-rz*.88),(x+1,y-ry*.48,z-rz*.88),.17,20,4,6)
  if mustache:
   for s in [-1,1]:self.ell((x+s*.8,y-1.9,z-rz-.2),(1.2,.55,.42),4,4,8,4)
 def hair(self,center=(0,53,1),size=(4.8,3.5,4.5),c=4):
  self.ell(center,size,c,4,12,5)
 def humanoid(self,shirt=8,pants=9,skin=0,head=True,boots=3,bare_legs=False):
  self.loft([(25,6,3.8),(29,5,3.2),(35,6,3.5),(40,7.8,4),(42,7.6,3.5)],shirt,2,12)
  self.loft([(23,6,3.8),(28,5.4,3.7)],pants,1,12)
  self.rod((0,41,0),(0,46,0),2,skin,3)
  for side,arm,fore,hand,thigh,calf,foot in [(1,6,7,8,13,14,15),(-1,10,11,12,16,17,18)]:
   x=side*4
   if bare_legs:
    self.loft([(13,2.8,2.7,x,0),(19,3.4,3,x,0)],skin,thigh,10)
    self.loft([(19,3.5,3.2,x,0),(25,3.6,3.5,x,0)],pants,thigh,10)
   else:self.loft([(13,2.8,2.7,x,0),(18,3.4,3,x,0),(25,3.6,3.5,x,0)],pants,thigh,10)
   self.loft([(3,2.3,2.5,x,0),(8,2.8,2.9,x,0),(13.8,2.8,2.7,x,0)],skin if bare_legs else pants,calf,10)
   self.ell((x,2,-1.4),(3,2,4.8),boots,foot,10,5)
   self.ell((side*9.5,39,0),(2.7,4,2.7),shirt,arm,10,5)
   self.rod((side*9.5,39,0),(side*11,31,0),2.2,skin,arm,10)
   self.rod((side*11,31,0),(side*11,23,0),1.9,skin,fore,10)
   self.ell((side*11,22.7,-.2),(2.1,2.8,1.8),skin,hand,10,5)
  if head:self.face_features(skin=skin)
 def export(self,height=56):
  factor=height/56
  if factor!=1:
   self.v=[[v*factor for v in p] for p in self.v]
   for b in self.bones:b['pivot']=[v*factor for v in b['pivot']]
  im=Image.new('RGB',(256,128))
  for i,c in enumerate(COLORS):im.paste(c,(i%8*32,i//8*32,i%8*32+32,i//8*32+32))
  root=P/'Meme-Pack';out=root/'Data/Textures';out.mkdir(parents=True,exist_ok=True);im.save(out/(self.stem+'.png'))
  model=dict(vertices=self.v,normals=self.n,uv=self.uv,faces=self.f,weights=self.w,bones=self.bones);(P/(self.stem+'-skin-model.json')).write_text(json.dumps(model));return export_skin(model,self.stem,root)
