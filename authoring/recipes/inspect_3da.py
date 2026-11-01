# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import struct,sys,json,pathlib
def inspect(filename):
 b=pathlib.Path(filename).read_bytes()
 u=lambda o:struct.unpack_from('<I',b,o)[0]
 f=lambda o,n:struct.unpack_from('<'+'f'*n,b,o)
 name=lambda o,n:b[o:o+n].split(b'\0',1)[0].decode('cp1250',errors='replace')
 assert b[:4]==b'3DA_' and u(4)==0x101
 count,frames=u(8),u(12)
 materials=[name(16+i*164,32) for i in range(u(5264))]
 pos=u(5276);nodes=[]
 for i in range(count):
  size=u(pos+152)
  if size<156 or pos+size>len(b):raise ValueError((i,pos,size,len(b)))
  pointers=[u(pos+j) for j in range(108,152,4)]
  tracks=[]
  for t in pointers[:3]:
   if t:
    tracks.append({'offset':t,'count':u(t+4),'type':u(t+8),'keyOffset':u(t+12),'firstKeyWords':[u(u(t+12)+j) for j in range(0,min(20,len(b)-u(t+12)),4)]})
  node={'index':i,'offset':pos,'size':size,'type':u(pos),'name':name(pos+4,32),'counts':[u(pos+j) for j in range(36,80,4)],'bounds':f(pos+80,6),'parent':struct.unpack_from('<h',b,pos+104)[0],'children':struct.unpack_from('<H',b,pos+106)[0],'pointers':pointers,'tracks':tracks}
  nodes.append(node);pos+=size
 return {'filename':str(filename),'bytes':len(b),'end':pos,'count':count,'frames':frames,'materials':materials,'nodes':nodes}
if __name__=='__main__':
 for file in sys.argv[1:]:
  result=inspect(file)
  pathlib.Path(file+'.structure.json').write_text(json.dumps(result,indent=2),encoding='utf8')
  print(json.dumps({k:v for k,v in result.items() if k!='nodes'},indent=2))
  for n in result['nodes']:print(n['index'],n['offset'],n['type'],n['name'],n['counts'],n['parent'],n['children'],'tracks',[(t['type'],t['count']) for t in n['tracks']])
