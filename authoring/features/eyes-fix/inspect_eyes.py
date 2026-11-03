"""Read current installed native lamb meshes without loading the game."""
from pathlib import Path
import argparse,hashlib,json,struct,sys
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
GAME=None
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'animal-identity'))
sys.path.insert(0,str(ROOT/'jagniellonia'))
sys.path.insert(0,str(ROOT/'base-maps'))
from native_variants import parse,worlds,F
from build_lamb_one import components
from native_tex import decode_level

def skin_world(data,node,matrices):
    out=[]
    for i in range(node['nv']):
        a,b,*vals=struct.unpack_from('<HH8f',data,node['pointers'][10]+i*36)
        out.append(((matrices[a]@np.r_[vals[:3],1])*vals[6]+(matrices[b]@np.r_[vals[3:6],1])*vals[7])[:3])
    return np.array(out)

def inspect(path):
    data=path.read_bytes();nodes=parse(data);matrices=worlds(data,nodes);report=[]
    for n in nodes:
        if n['type']!=2 or not n['name'].startswith('mis_'):continue
        ptr=n['pointers'];points=skin_world(data,n,matrices)
        faces=np.frombuffer(data,'<u2',count=n['nf']*3,offset=ptr[4]).reshape(-1,3)
        uvfaces=np.frombuffer(data,'<u2',count=n['nf']*3,offset=ptr[6]).reshape(-1,3)
        uv=np.frombuffer(data,'<f4',count=n['nuv']*2,offset=ptr[7]).reshape(-1,2)
        groups=[]
        for ids in components(n['nv'],faces):
            select=np.all(np.isin(faces,ids),axis=1);up=uv[uvfaces[select]]
            groups.append(dict(vertices=[int(i) for i in ids],faces=faces[select].tolist(),uvfaces=uvfaces[select].tolist(),
                points=points[ids].tolist(),center=points[ids].mean(0).tolist(),extent=np.ptp(points[ids],axis=0).tolist(),
                uvbounds=[up.reshape(-1,2).min(0).tolist(),up.reshape(-1,2).max(0).tolist()]))
        report.append(dict(node=n['name'],groups=groups,
            head_near_eye=[dict(id=i,p=p.tolist()) for i,p in enumerate(points) if 90<p[1]<102 and abs(p[0])<15]))
    return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),meshes=report)

def main():
    global HERE,GAME
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();GAME=args.input.resolve(strict=True);HERE=args.output.resolve()
    assert not HERE.exists() and not HERE.is_relative_to(GAME), 'Choose a fresh isolated output directory'
    HERE.mkdir(parents=True)
    records=[inspect(GAME/f'Data/Meshes/Animals/cx_jagniaki_{i}.3da') for i in range(7)]
    (HERE/'current-native-analysis.json').write_text(json.dumps(records,indent=2)+'\n')
    tex=GAME/'Data/Textures/Tshirts/cx_jagniaki_01.tex'
    im=decode_level(tex.read_bytes())
    im.crop((414,0,512,85)).resize((784,680),Image.Resampling.NEAREST).save(HERE/'current-native-eye-texels.png')
    print(json.dumps(dict(models=[dict(path=r['path'],sha256=r['sha256']) for r in records],
        groups=[dict(node=m['node'],islands=[dict(n=len(g['vertices']),center=np.round(g['center'],3).tolist(),extent=np.round(g['extent'],3).tolist(),uv=g['uvbounds']) for g in m['groups'] if len(g['vertices'])<60]) for m in records[0]['meshes']])))

if __name__=='__main__':main()
