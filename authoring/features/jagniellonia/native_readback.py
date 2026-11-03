"""Native readback CPU renderer adapted from animal-identity/render_readback.py; no import-time writes."""
from pathlib import Path
import math,struct,sys
import numpy as np
from PIL import Image,ImageDraw
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"animal-identity"))
from native_variants import parse,worlds,U,F

def native_mesh(path,frame=0):
    data=path.read_bytes();nodes=parse(data);matrices=worlds(data,nodes,frame);result=[]
    for node in nodes:
        if node['type']!=2 or not node['nv'] or not node['name'].endswith('_0'):continue
        vertices=[];skin=node['pointers'][10]
        for i in range(node['nv']):
            a,b,*values=struct.unpack_from('<HH8f',data,skin+i*36);va,vb=values[:3],values[3:6];wa,wb=values[6:]
            vertices.append(((matrices[a]@np.array([*va,1]))*wa+(matrices[b]@np.array([*vb,1]))*wb)[:3])
        vertices=np.array(vertices)
        faces=np.frombuffer(data,'<u2',count=node['nf']*3,offset=node['pointers'][4]).reshape(-1,3)
        uvfaces=np.frombuffer(data,'<u2',count=node['nf']*3,offset=node['pointers'][6]).reshape(-1,3)
        uvs=np.frombuffer(data,'<f4',count=U(data,node['offset']+64)*2,offset=node['pointers'][7]).reshape(-1,2)
        materials=np.frombuffer(data,'<u2',count=node['nf'],offset=node['pointers'][5])
        for face,uvface,material in zip(faces,uvfaces,materials):
            if material==0:result.append((vertices[face],uvs[uvface]))
    assert result
    return result

def render(mesh,texture,direction=(0,0,-1),size=(250,320),scale=2.7,center=(0,40,0)):
    width,height=size;image=np.full((height,width,3),(39,56,48),dtype=float);depth=np.full((height,width),-np.inf)
    direction=np.array(direction,dtype=float);direction/=np.linalg.norm(direction);up=np.array((0,1,0));right=np.cross(up,direction);right/=np.linalg.norm(right)
    light=np.array((-.3,.8,-.5));light/=np.linalg.norm(light)
    tex=np.asarray(texture.convert('RGB'));th,tw,_=tex.shape
    for vertices,uvs in mesh:
        vertices=vertices-np.array(center);x=vertices@right*scale+width/2;y=height/2-vertices@up*scale;z=vertices@direction
        left=max(0,int(math.floor(x.min())));rightmost=min(width-1,int(math.ceil(x.max())))
        top=max(0,int(math.floor(y.min())));bottom=min(height-1,int(math.ceil(y.max())))
        if left>rightmost or top>bottom:continue
        denominator=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(denominator)<1e-8:continue
        px,py=np.meshgrid(np.arange(left,rightmost+1)+.5,np.arange(top,bottom+1)+.5)
        a=((y[1]-y[2])*(px-x[2])+(x[2]-x[1])*(py-y[2]))/denominator
        b=((y[2]-y[0])*(px-x[2])+(x[0]-x[2])*(py-y[2]))/denominator;c=1-a-b
        zz=a*z[0]+b*z[1]+c*z[2];current=depth[top:bottom+1,left:rightmost+1]
        inside=(a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)&(zz>current)
        if not inside.any():continue
        u=(a*uvs[0,0]+b*uvs[1,0]+c*uvs[2,0]);v=(a*uvs[0,1]+b*uvs[1,1]+c*uvs[2,1])
        tx=np.clip((u*tw).astype(int),0,tw-1);ty=np.clip((v*th).astype(int),0,th-1)
        normal=np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0]);length=np.linalg.norm(normal)
        shade=.7+.3*abs(float(normal@light/max(length,1e-9)))
        region=image[top:bottom+1,left:rightmost+1];region[inside]=tex[ty[inside],tx[inside]]*shade;current[inside]=zz[inside]
    return Image.fromarray(np.clip(image,0,255).astype('uint8'))
