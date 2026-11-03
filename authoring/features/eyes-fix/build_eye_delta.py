"""Eye-only delta against the current installed native lamb binaries.

No game, original feature, INI, bitmap, kit, animation, rig or non-eye normal
is modified. Existing eyes become shallow surface-fitting caps, solid white;
new small circular pupils sample an existing solid-black native atlas texel.
"""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
GAME=None
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'animal-identity'),str(ROOT/'jagniellonia')]
from native_variants import parse,worlds,U,F,face_normals
from build_lamb_one import components
from inspect_eyes import skin_world

def sha(data):return hashlib.sha256(data).hexdigest()
def cross2(a,b):return a[0]*b[1]-a[1]*b[0]

def front_hit(vertices,faces,xy):
    """Frontmost exact barycentric triangle hit along +Z at an XY location."""
    tri=vertices[faces];a=tri[:,0,:2];b=tri[:,1,:2];c=tri[:,2,:2]
    v0=b-a;v1=c-a;v2=np.array(xy)-a
    den=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]
    valid=np.abs(den)>1e-9
    x=np.zeros(len(faces));y=x.copy()
    x[valid]=(v2[valid,0]*v1[valid,1]-v2[valid,1]*v1[valid,0])/den[valid]
    y[valid]=(v0[valid,0]*v2[valid,1]-v0[valid,1]*v2[valid,0])/den[valid]
    hit=valid&(x>=-1e-6)&(y>=-1e-6)&(x+y<=1+1e-6)
    if not hit.any():raise ValueError('No head/eye surface below '+repr(xy))
    z=(1-x-y)*tri[:,0,2]+x*tri[:,1,2]+y*tri[:,2,2]
    i=int(np.argmax(np.where(hit,z,-np.inf)))
    n=np.cross(tri[i,1]-tri[i,0],tri[i,2]-tri[i,0]);n/=np.linalg.norm(n)
    if n[2]<0:n=-n
    return float(z[i]),n

def identify(data,node,matrices):
    p=node['pointers'];pts=skin_world(data,node,matrices)
    faces=np.frombuffer(data,'<u2',count=node['nf']*3,offset=p[4]).reshape(-1,3)
    uvf=np.frombuffer(data,'<u2',count=node['nf']*3,offset=p[6]).reshape(-1,3)
    uv=np.frombuffer(data,'<f4',count=node['nuv']*2,offset=p[7]).reshape(-1,2)
    groups=components(node['nv'],faces);body=max(groups,key=len);eye=[]
    for ids in groups:
        select=np.all(np.isin(faces,ids),axis=1);cen=pts[ids].mean(0)
        tex=uv[uvf[select]].reshape(-1,2)
        if len(ids)<40 and cen[1]>94 and tex[:,0].min()>.9 and tex[:,1].max()<.2:
            assert not set(uvf[select].ravel()).intersection(uvf[~select].ravel())
            eye.append(dict(ids=np.array(ids,dtype=int),select=select,center=cen))
    return pts,faces,uvf,eye,np.all(np.isin(faces,body),axis=1)

def append_pupil_node(data,template,matrices,lod,eyes):
    """Append one Head-skinned pupil node per existing eye LOD; no old offsets move."""
    nodes=parse(data);head=next(n['index'] for n in nodes if n['name']=='Bip01 Head')
    ni=np.linalg.inv(matrices[template['index']]);hi=np.linalg.inv(matrices[head])
    verts=[];faces=[];details=[]
    for e in eyes:
        # Circle in front projection. Depth conforms to the actual white cap,
        # leaving only 0.018 native units separation to prevent Z fighting.
        center=e['pupil_center'].copy();radius=.94;count=16 if lod==0 else 12
        ring=[center+radius*np.array((math.cos(i*2*math.pi/count),math.sin(i*2*math.pi/count))) for i in range(count)]
        triangles=e['points'][e['faces']];patch_count=0
        for triangle in triangles:
            # Clip the circle to EACH original white front triangle. This
            # follows every surface crease exactly rather than bridging the
            # convex cap with a flat board, which the white mesh would occlude.
            poly=[p[:2].copy() for p in triangle]
            for k in range(count):
                a,b=ring[k],ring[(k+1)%count];edge=b-a;new=[]
                for q,r in zip(poly,poly[1:]+poly[:1]):
                    dq=cross2(edge,q-a);dr=cross2(edge,r-a)
                    if dq>=-1e-8:new.append(q)
                    if (dq>=0)!=(dr>=0):new.append(q+(r-q)*float(dq/(dq-dr)))
                poly=new
                if len(poly)<3:break
            if len(poly)<3:continue
            a,b,c=triangle;det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if abs(det)<1e-9:continue
            def z_at(q):
                v=q-a[:2];s=(v[0]*(c[1]-a[1])-v[1]*(c[0]-a[0]))/det
                t=((b[0]-a[0])*v[1]-(b[1]-a[1])*v[0])/det
                return a[2]+s*(b[2]-a[2])+t*(c[2]-a[2])
            middle=np.mean(poly,axis=0);front,_=front_hit(e['points'],e['faces'],middle)
            if abs(z_at(middle)-front)>.0001:continue
            # Normalize winding to +Z; native backface culling must see front.
            signed=sum(float(cross2(p,q)) for p,q in zip(poly,poly[1:]+poly[:1]))
            if signed<0:poly.reverse()
            offset=len(verts);verts.extend([q[0],q[1],z_at(q)+.025] for q in poly)
            faces.extend((offset,offset+i,offset+i+1) for i in range(1,len(poly)-1));patch_count+=1
        details.append(dict(center_xy=center.tolist(),radius=radius,segments=count,
            conformal_surface='exact clipped white cap triangles',surface_patches=patch_count))
    world=np.array(verts);face=np.array(faces,dtype='<u2')
    cached=(ni@np.column_stack((world,np.ones(len(world)))).T).T[:,:3]
    local=(hi@np.column_stack((world,np.ones(len(world)))).T).T[:,:3]
    header=bytearray(data[template['offset']:template['offset']+156]);name=('Oczy_'+str(lod)).encode('ascii')
    header[4:36]=name+b'\0'*(32-len(name))
    counts=[len(world),len(face),0,len(face),0,0,0,1,0,0,2]
    for i,v in enumerate(counts):struct.pack_into('<I',header,36+i*4,v)
    struct.pack_into('<6f',header,80,*cached.min(0),*cached.max(0));struct.pack_into('<hH',header,104,-1,0)
    for i in range(11):struct.pack_into('<I',header,108+4*i,0)
    start=len(data);buf=header
    def add(index,blob):
        while len(buf)%4:buf.append(0)
        pointer=start+len(buf);buf.extend(blob);struct.pack_into('<I',buf,108+index*4,pointer);return pointer
    add(4,face.tobytes());add(5,b'\0\0'*len(face));add(6,b'\0\0'*len(face)*3)
    add(7,struct.pack('<2f',494.5/512,37.5/512))
    add(8,np.asarray(cached,dtype='<f4').tobytes());add(9,np.asarray(face_normals(cached,face),dtype='<f4').tobytes())
    add(10,b''.join(struct.pack('<HH8f',head,head,*p,*p,.5,.5) for p in local))
    for index,dim in enumerate((3,4,3)):
        old=template['pointers'][index];count,kind,key=U(data,old+4),U(data,old+8),U(data,old+12)
        stride={1:24+12*dim,2:4+12*dim,3:4+4*dim}[kind]
        track=data[old:key+count*stride];new=add(index,track);struct.pack_into('<I',buf,new-start+12,new+key-old)
    struct.pack_into('<I',buf,152,len(buf));out=bytearray(data);out.extend(buf);struct.pack_into('<I',out,8,len(nodes)+1)
    assert len(parse(bytes(out)))==len(nodes)+1
    return bytes(out),dict(name=name.decode(),vertices=len(world),triangles=len(face),head_bone=head,eyes=details)

def fix(data):
    nodes=parse(data);matrices=worlds(data,nodes);out=bytearray(data);allowed=np.zeros(len(data),bool);report=[];pupils=[]
    assert not any(n['name'].startswith('Oczy_') for n in nodes), 'Eye delta already applied; refuse a second shrink or duplicate pupils'
    for node in nodes:
        if node['type']!=2 or not node['name'].startswith('mis_'):continue
        points,faces,uvfaces,eyes,body=identify(data,node,matrices)
        if not eyes:
            report.append(dict(node=node['name'],eye_vertices=0,action='source low LOD has no eye islands; retained unchanged'))
            continue
        assert len(eyes)==2
        ptr=node['pointers'];cache=np.frombuffer(data,'<f4',count=node['nv']*3,offset=ptr[8]).reshape(-1,3).copy()
        newcache=cache.copy();target=points.copy();rows=[];touched=[];uvindices=set()
        for eye in eyes:
            ids=eye['ids'];center=eye['center'];relative=points[ids]-center
            # Preserve the authored round 16/7-vertex topology, reduced to72%.
            newxy=center[:2]+relative[:,:2]*.72
            z=relative[:,2];z=(z-z.min())/(z.max()-z.min())*2-1
            headz=[]
            for j,xy in enumerate(newxy):
                surface,_=front_hit(points,faces[body],xy);headz.append(surface)
                target[ids[j]]=[xy[0],xy[1],surface-.25+z[j]*1.3]
            oldfront=[front_hit(points,faces[body],p[:2])[0] for p in points[ids]]
            rows.append(dict(side='left' if center[0]<0 else 'right',vertices=ids.tolist(),
                old_center=center.tolist(),new_center=target[ids].mean(0).tolist(),
                old_extent=np.ptp(points[ids],axis=0).tolist(),new_extent=np.ptp(target[ids],axis=0).tolist(),
                old_clearance=np.round(points[ids,2]-oldfront,6).tolist(),
                new_clearance=np.round(target[ids,2]-headz,6).tolist()))
            touched.extend(ids);uvindices.update(int(v) for v in uvfaces[eye['select']].ravel())
            # Same forward gaze in both eyes and both LODs. The seven-vertex
            # source reduction has an asymmetric front-vertex distribution;
            # choosing its two highest vertices would move one pupil upward.
            pupil_xy=center[:2]+np.array((0,-.65))
            pupils.append((int(node['name'][-1]),node,dict(center=np.r_[newxy.mean(0),0],pupil_center=pupil_xy,points=target.copy(),faces=faces[eye['select']].copy())))
        for i in touched:
            at=ptr[10]+int(i)*36;a,b,*v=struct.unpack_from('<HH8f',data,at)
            delta=target[i]-points[i]
            va=np.array(v[:3])+np.linalg.inv(matrices[a])[:3,:3]@delta
            vb=np.array(v[3:6])+np.linalg.inv(matrices[b])[:3,:3]@delta
            struct.pack_into('<6f',out,at+4,*va,*vb);allowed[at+4:at+28]=True
            newcache[i]+=np.linalg.inv(matrices[node['index']])[:3,:3]@delta
            at=ptr[8]+int(i)*12;struct.pack_into('<3f',out,at,*newcache[i]);allowed[at:at+12]=True
        oldgeom=face_normals(cache,faces);newgeom=face_normals(newcache,faces)
        for i in touched:
            at=ptr[9]+int(i)*12;n=np.array(F(data,at,3))+newgeom[i]-oldgeom[i];n/=np.linalg.norm(n)
            struct.pack_into('<3f',out,at,*n);allowed[at:at+12]=True
        for i in uvindices:
            at=ptr[7]+i*8;struct.pack_into('<2f',out,at,480.5/512,40.5/512);allowed[at:at+8]=True
        # Existing bounds are conservative because the new eye is contained.
        # Deliberately keep bounds, every other normal and every non-eye byte.
        report.append(dict(node=node['name'],eyes=rows,eye_vertices=len(touched),uv_indices=sorted(uvindices)))
    assert sorted(l for l,n,e in pupils)==[0,0,1,1], 'Expected exactly two eyes in each of original LOD0/LOD1'
    changed=np.frombuffer(data,'u1')!=np.frombuffer(out,'u1');assert not np.any(changed&~allowed)
    updated=bytes(out);added=[]
    for lod in sorted(set(l for l,n,e in pupils)):
        group=[e for l,n,e in pupils if l==lod];template=next(n for l,n,e in pupils if l==lod)
        updated,detail=append_pupil_node(updated,template,matrices,lod,group);added.append(detail)
    # Only the file-global node count may differ before original nodes.
    finalprefix=bytearray(updated[:len(data)]);finalprefix[8:12]=data[8:12]
    assert not np.any((np.frombuffer(data,'u1')!=np.frombuffer(finalprefix,'u1'))&~allowed)
    return updated,dict(meshes=report,new_eye_only_nodes=added,non_eye_original_bytes_identical=True,
        old_bytes=len(data),new_bytes=len(updated),changed_original_bytes=int(changed.sum()),
        textures_unchanged=True,rig_weights_tracks_topology_of_original_nodes_unchanged=True,
        only_existing_eye_positions_normals_and_exclusive_uvs_changed=True)

def main():
    global HERE,GAME
    parser=argparse.ArgumentParser();parser.add_argument('--slots',default='0,1,2,3,4,5,6')
    parser.add_argument('--input',required=True,type=Path,help='Raw seven-model overlay before eye repair')
    parser.add_argument('--output',required=True,type=Path,help='Fresh isolated output directory')
    parser.add_argument('--expected-inputs',type=Path,default=HERE/'expected-inputs.json')
    args=parser.parse_args();GAME=args.input.resolve(strict=True);HERE=args.output.resolve()
    assert not HERE.exists() and not HERE.is_relative_to(GAME), 'Choose a fresh isolated output directory'
    HERE.mkdir(parents=True)
    slots=[int(i) for i in args.slots.split(',')];assert slots in ([0],list(range(7))), 'Only candidate0 or the complete approved seven-model delivery'
    delivery=len(slots)==7
    baseline=json.loads(args.expected_inputs.read_text())
    target=HERE/('delivery/overlay/Data/Meshes/Animals' if delivery else 'candidate0/Data/Meshes/Animals');target.mkdir(parents=True,exist_ok=True)
    source=HERE/'source';source.mkdir(exist_ok=True);records=[]
    for slot in slots:
        path=GAME/f'Data/Meshes/Animals/cx_jagniaki_{slot}.3da';data=path.read_bytes()
        assert sha(data)==baseline[slot]['sha256'], 'Current installed source drift'
        snapshot=source/path.name
        if snapshot.exists():assert snapshot.read_bytes()==data
        else:snapshot.write_bytes(data)
        changed,proof=fix(data);out=target/path.name;out.write_bytes(changed)
        if slot==0:assert sha(changed)=='ee14840c195ca1451938b4221d7044edc03fce74bcece331b9428bc817ade1de', 'Approved candidate0 drift'
        records.append(dict(slot=slot,source=str(path),input_sha256=sha(data),output=str(out),output_sha256=sha(changed),proof=proof))
    textures=[]
    for i in range(1,6):
        path=GAME/f'Data/Textures/Tshirts/cx_jagniaki_{i:02d}.tex';textures.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path.read_bytes())))
    record=dict(status='SEVEN eye-only distribution models; awaiting root native test' if delivery else 'MODEL0 offline direction approved',models=records,textures_read_only=textures,native_runtime_verified=False)
    manifest=HERE/('delivery/build-manifest.json' if delivery else 'candidate0-manifest.json')
    manifest.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(manifest=str(manifest),models=len(records),output_sha256=[r['output_sha256'] for r in records])))

if __name__=='__main__':main()
