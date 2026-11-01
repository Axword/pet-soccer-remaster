"""Independent reader/checker for the compacted exports (does not import writer)."""
import argparse,hashlib,json,struct
from pathlib import Path

def uint(data,at):return int.from_bytes(data[at:at+4],'little')
def sha(data):return hashlib.sha256(data).hexdigest()

def read(path):
 data=path.read_bytes();assert data[:8]==b'3DA_\x01\x01\0\0'
 offset=uint(data,5276);nodes=[]
 for _ in range(uint(data,8)):
  nbytes=uint(data,offset+152);nodes.append((offset,nbytes));offset+=nbytes
 assert offset==len(data)
 return data,nodes

def materialized(data,start):
 nv=uint(data,start+36);nf=uint(data,start+40)
 ptr=[uint(data,start+at) for at in range(108,152,4)]
 streams={}
 for index,p in enumerate(ptr):
  if not p:continue
  end=min([q for q in ptr if q>p]+[len(data)])
  streams[index]=data[p:end]
 attrs=[]
 for i in range(nv):
  attrs.append(streams[8][i*12:i*12+12]+streams[9][i*12:i*12+12]+
   streams[7][i*8:i*8+8]+streams[10][i*36:i*36+36])
 draw=bytearray()
 for tri in range(nf):
  for corner in range(3):
   at=(tri*3+corner)*2
   vi=int.from_bytes(streams[4][at:at+2],'little')
   ui=int.from_bytes(streams[6][at:at+2],'little')
   assert vi==ui and vi<nv
   draw.extend(attrs[vi])
 normalized=[]
 for i in range(3):
  payload=streams[i]
  normalized.append(payload[:12]+(uint(payload,12)-ptr[i]).to_bytes(4,'little')+payload[16:])
 return bytes(draw),streams[5],normalized

def verify(a,b):
 old,on=read(a);new,nn=read(b);assert len(on)==len(nn)
 assert old[:5272]==new[:5272] and old[5276:5344]==new[5276:5344]
 for k in range(len(on)-1):
  o,os=on[k];n,ns=nn[k];assert old[o:o+os]==new[n:n+ns]
 o,os=on[-1];n,ns=nn[-1]
 assert old[o:o+36]==new[n:n+36] and old[o+80:o+108]==new[n+80:n+108]
 olddraw,oldgroups,oldanim=materialized(old,o)
 newdraw,newgroups,newanim=materialized(new,n)
 assert olddraw==newdraw,'A drawn corner attribute changed'
 assert oldgroups==newgroups,'Material group changed'
 assert oldanim==newanim,'Animation bytes changed'
 assert uint(old,o+40)==uint(new,n+40),'Triangle count changed'
 return dict(file=a.name,expanded_draw_sha256=sha(olddraw),all_corner_attributes_exact=True,
  material_groups_exact=True,all_animation_bytes_exact=True,all_non_skin_nodes_exact=True,
  vertices_before=uint(old,o+36),vertices_after=uint(new,n+36),
  source_bytes=len(old),output_bytes=len(new))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 rows=[verify(a.source/f.name,f) for f in sorted(a.output.glob('*.3da'))]
 assert rows
 (a.output/'independent-verification.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 print('PASS',len(rows),'files; exact expanded triangles, skin, normals, UVs, groups, animations and other nodes')
