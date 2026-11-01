"""Authored uniform scale of fresh custom 0x101 models, exclusively into this folder.

All position values AND interpolation tangents are scaled, keeping the existing
rig, indices, weights, rotations and frame times. Original engine helpers move
with the larger rig; callers must retain collider normalization and verify ball
attachment/throw-in height in the actual engine.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import argparse, pathlib, struct, sys, json, hashlib, math, shutil
P=pathlib.Path(__file__).resolve().parents[3]
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from inspect_3da import inspect

def sha(b):return hashlib.sha256(b).hexdigest()

def scaled(source,factor):
    before=source.read_bytes();b=bytearray(before);r=inspect(source)
    touched=set();counts={};ignored=[]
    def vec(at,role,optional=False):
        if at in touched:return
        value=struct.unpack_from('<3f',b,at)
        # Old Max default caches can contain uninitialized data. They are not
        # animation keys; retain their exact bytes instead of rewriting junk.
        if not all(math.isfinite(x) and abs(x)<1e10 for x in value):
            if optional:ignored.append({'offset':at,'role':role});return
            raise ValueError((source,'nonfinite/invalid geometric vector',at,role,value))
        struct.pack_into('<3f',b,at,*(x*factor for x in value))
        touched.add(at);counts[role]=counts.get(role,0)+1
    vec(5280,'global_bounds');vec(5292,'global_bounds')
    for n in r['nodes']:
        off=n['offset'];vec(off+80,'node_bounds',True);vec(off+92,'node_bounds',True)
        pos=n['pointers'][0]
        if pos:
            count,kind,key=struct.unpack_from('<III',b,pos+4)
            assert kind in (1,2,3)
            if key-pos>=28:vec(pos+16,'position_default',True)
            stride={1:60,2:40,3:16}[kind]
            offsets={1:(24,36,48),2:(4,16,28),3:(4,)}[kind]
            for i in range(count):
                for j,delta in enumerate(offsets):vec(key+i*stride+delta,'position_value' if j==0 else 'position_tangent')
        nv=n['counts'][0]
        ptr=n['pointers'][8]
        if ptr and nv:
            for i in range(nv):vec(ptr+i*12,'vertex_position')
        if n['type']==2:
            skin=n['pointers'][10];assert skin and nv
            for i in range(nv):
                vec(skin+i*36+4,'skin_local_position')
                vec(skin+i*36+16,'skin_local_position')
    assert len(before)==len(b)
    return bytes(b),{'changed_vectors':counts,'ignored_uninitialized_optional_cache':ignored,'changed_bytes':sum(x!=y for x,y in zip(before,b))}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--factor',type=float,default=2.0);ap.add_argument('--species',type=int,nargs='*');ap.add_argument('--all',action='store_true');args=ap.parse_args()
    assert 1<args.factor<=3
    inv=json.loads((D/'inventory.json').read_text())
    if not args.all:
        assert args.species,'Use --species for prototype or --all after its visual review'
        inv=[r for r in inv if r['species'] in args.species]
    result=[]
    for row in inv:
        src=pathlib.Path(row['source']);raw=src.read_bytes();assert sha(raw)==row['sha256'],('Source changed; refresh inventory',src)
        rel=pathlib.Path(row['relative']);backup=D/'backups'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert sha(backup.read_bytes())==sha(raw),'Fresh backup differs'
        else:shutil.copy2(src,backup)
        output,stats=scaled(src,args.factor);dest=D/'Pack'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(output)
        after=inspect(dest);assert after['end']==len(output)
        assert after['frames']==row['frames'] and after['count']==row['nodes']
        result.append({**row,'factor':args.factor,'output':str(dest),'output_sha256':sha(output),'output_bounds':struct.unpack_from('<6f',output,5280),**stats})
        print('SCALED',row['species'],row['name'],flush=True)
    (D/('scale-manifest.json' if args.all else 'prototype-manifest.json')).write_text(json.dumps({'factor':args.factor,'models':result,'collider_policy':'Integrator retains NormalizePhysics; this does not change that collider code.','attachment_impact':'Native helper/bone attachment locations are scaled too. Throw-in ball height must be tested; this is not claimed gameplay neutral.','original_species_0_to_11_changed':False},indent=2))

if __name__=='__main__':main()
