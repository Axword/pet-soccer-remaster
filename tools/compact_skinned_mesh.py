"""Losslessly weld bit-identical skin vertices in the reviewed 0x101 3DA export.

The only supported edit is the final, single two-influence skinned node emitted
by export_skinned_character.py. Other nodes and animation payloads stay exact.
No source file is changed. Output must be separate and not already exist.
"""
from pathlib import Path
import argparse, hashlib, json, struct

U=lambda b,o:struct.unpack_from('<I',b,o)[0]
S=lambda x:hashlib.sha256(x).hexdigest()

def inspect(raw):
 assert raw[:4]==b'3DA_' and U(raw,4)==0x101,'Unsupported model signature/version'
 pos=U(raw,5276);nodes=[]
 for index in range(U(raw,8)):
  size=U(raw,pos+152);assert size>=156 and pos+size<=len(raw)
  nodes.append(dict(index=index,base=pos,size=size,kind=U(raw,pos),
    ptrs=[U(raw,pos+j) for j in range(108,152,4)],counts=[U(raw,pos+j) for j in range(36,80,4)]))
  pos+=size
 assert pos==len(raw),'Trailing or missing bytes'
 return nodes

def corners(raw,node):
 nv,nf=node['counts'][:2];p=node['ptrs'];assert node['counts'][7]==nv
 face1=raw[p[4]:p[4]+nf*6];face2=raw[p[6]:p[6]+nf*6]
 assert face1==face2,'This exporter uses a shared vertex/UV index stream'
 vertices=[]
 for i in range(nv):
  vertices.append(raw[p[8]+i*12:p[8]+(i+1)*12]+
    raw[p[9]+i*12:p[9]+(i+1)*12]+raw[p[7]+i*8:p[7]+(i+1)*8]+
    raw[p[10]+i*36:p[10]+(i+1)*36])
 indices=struct.unpack('<'+'H'*(nf*3),face1)
 assert all(i<nv for i in indices)
 digest=hashlib.sha256()
 for i in indices:digest.update(vertices[i])
 return vertices,indices,digest.hexdigest()

def compact(source,output):
 source=Path(source).resolve();output=Path(output).resolve()
 assert source!=output and not output.exists(),'Use a new separate output path'
 raw=source.read_bytes();nodes=inspect(raw)
 skins=[n for n in nodes if n['kind']==2]
 assert len(skins)==1 and skins[0] is nodes[-1],'Only single final skin exports supported'
 node=skins[0];p=node['ptrs'];nv,nf=node['counts'][:2]
 assert node['counts']==[nv,nf,0,nf,0,0,0,nv,0,0,2],node['counts']
 assert p[3]==0 and all(p[j] for j in (0,1,2,4,5,6,7,8,9,10))
 vertices,indices,before_digest=corners(raw,node)
 unique=[];ids={};remap=[]
 for attributes in vertices:
  if attributes not in ids:ids[attributes]=len(unique);unique.append(attributes)
  remap.append(ids[attributes])
 count=len(unique);assert count<=65535
 groups=raw[p[5]:p[5]+nf*2]
 replacements={
  4:struct.pack('<'+'H'*len(indices),*(remap[i] for i in indices)),
  5:groups,
  6:struct.pack('<'+'H'*len(indices),*(remap[i] for i in indices)),
  7:b''.join(v[24:32] for v in unique),
  8:b''.join(v[:12] for v in unique),
  9:b''.join(v[12:24] for v in unique),
  10:b''.join(v[32:] for v in unique),
 }
 starts=sorted((offset,index) for index,offset in enumerate(p) if offset)
 assert starts[0][0]==node['base']+156
 assert len({offset for offset,index in starts})==len(starts),'Aliased streams unsupported'
 old_lengths={i:(starts[k+1][0] if k+1<len(starts) else len(raw))-o for k,(o,i) in enumerate(starts)}
 expected={4:nf*6,5:nf*2,6:nf*6,7:nv*8,8:nv*12,9:nv*12,10:nv*36}
 assert all(old_lengths[i]==length for i,length in expected.items()),old_lengths
 base=node['base'];block=bytearray(raw[base:base+156]);track_hashes={}
 for old_offset,index in starts:
  new_offset=base+len(block)
  struct.pack_into('<I',block,108+index*4,new_offset)
  payload=bytearray(raw[old_offset:old_offset+old_lengths[index]])
  if index in replacements:payload=bytearray(replacements[index])
  if index in (0,1,2):
   key_offset=U(payload,12);assert old_offset<=key_offset<old_offset+len(payload)
   normalized=bytes(payload[:12])+struct.pack('<I',key_offset-old_offset)+bytes(payload[16:])
   track_hashes[str(index)]=S(normalized)
   struct.pack_into('<I',payload,12,key_offset-old_offset+new_offset)
  block.extend(payload)
 struct.pack_into('<I',block,36,count)
 struct.pack_into('<I',block,64,count)
 struct.pack_into('<I',block,152,len(block))
 result=bytearray(raw[:base])+block
 struct.pack_into('<I',result,5272,U(raw,5272)-(nv-count))
 new_nodes=inspect(result);new_node=new_nodes[-1]
 _,new_indices,after_digest=corners(result,new_node)
 assert before_digest==after_digest,'Expanded triangle attributes changed'
 assert len(new_indices)==len(indices)
 assert result[base+new_node['ptrs'][5]-base:base+new_node['ptrs'][5]-base+nf*2]==groups
 assert raw[U(raw,5276):base]==result[U(raw,5276):base],'Non-skin nodes changed'
 assert raw[:5272]==result[:5272] and raw[5276:base]==result[5276:base]
 assert raw[base:base+36]==result[base:base+36]
 assert raw[base+80:base+108]==result[base+80:base+108],'Bounds or hierarchy changed'
 for index in (0,1,2):
  start=new_node['ptrs'][index];length=old_lengths[index]
  payload=bytes(result[start:start+length]);normalized=payload[:12]+struct.pack('<I',U(payload,12)-start)+payload[16:]
  assert S(normalized)==track_hashes[str(index)],'Skin track payload changed'
 output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
 return dict(file=source.name,source=str(source),output=str(output),source_sha256=S(raw),output_sha256=S(result),
  bytes_before=len(raw),bytes_after=len(result),bytes_saved=len(raw)-len(result),
  skin_vertices_before=nv,skin_vertices_after=count,triangles=nf,
  reduction_percent=round((nv-count)*100/nv,2),expanded_corner_sha256=before_digest,
  exact_triangle_attributes=True,non_skin_nodes_exact=True,skin_animation_sha256=track_hashes,
  hierarchy_and_bounds_exact=True,original_file_unchanged=S(source.read_bytes())==S(raw))

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--input',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--pattern',default='cx_w3_*.3da')
 a=ap.parse_args();rows=[]
 assert a.input.resolve()!=a.output.resolve()
 for f in sorted(a.input.glob(a.pattern)):
  row=compact(f,a.output/f.name);rows.append(row)
  print(f.name,row['skin_vertices_before'],'->',row['skin_vertices_after'],row['reduction_percent'],'%',flush=True)
 assert rows,'No models matched'
 (a.output/'compact-report.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 print('Exact expanded attributes; identical animation/hierarchy; saved',sum(r['bytes_saved'] for r in rows),'bytes')

if __name__=='__main__':main()
