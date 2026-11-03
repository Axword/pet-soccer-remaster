"""Conservative native 0x101 skin morphs. No Blender or game process required.

Only skin-local geometry positions/normals/bounds are changed. Bone IDs, blend
weights, animation bytes, topology, material names, UVs and LOD structure remain.
"""
from __future__ import annotations
import bisect,hashlib,math,struct
from pathlib import Path
import numpy as np

U=lambda b,o:struct.unpack_from('<I',b,o)[0]
F=lambda b,o,n:struct.unpack_from('<'+'f'*n,b,o)

def parse(data:bytes):
    assert data[:8]==b'3DA_\x01\x01\x00\x00'
    nodes=[];at=U(data,5276)
    for index in range(U(data,8)):
        size=U(data,at+152);assert size>=156 and at+size<=len(data)
        nodes.append(dict(index=index,offset=at,size=size,type=U(data,at),
            name=data[at+4:at+36].split(b'\0',1)[0].decode('cp1250'),
            nv=U(data,at+36),nf=U(data,at+40),nuv=U(data,at+64),
            parent=struct.unpack_from('<h',data,at+104)[0],
            pointers=[U(data,at+j) for j in range(108,152,4)]))
        at+=size
    assert at==len(data)
    return nodes

def track(data,pointer,dim,default):
    if not pointer:return [0],[np.array(default,dtype=float)]
    count,kind,start=U(data,pointer+4),U(data,pointer+8),U(data,pointer+12)
    stride={1:24+12*dim,2:4+12*dim,3:4+4*dim}[kind]
    offset=24 if kind==1 else 4
    return ([U(data,start+i*stride) for i in range(count)],
        [np.array(F(data,start+i*stride+offset,dim),dtype=float) for i in range(count)])

def quaternion_matrix(q):
    x,y,z,w=-q[0],-q[1],-q[2],q[3]
    length=math.sqrt(x*x+y*y+z*z+w*w)
    if length<1e-8:return np.eye(4)
    x,y,z,w=[v/length for v in (x,y,z,w)]
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]])

def worlds(data,nodes,frame=0):
    output=[]
    for node in nodes:
        values=[]
        for pointer,dim,default in zip(node['pointers'][:3],[3,4,3],[(0,0,0),(0,0,0,1),(1,1,1)]):
            frames,keys=track(data,pointer,dim,default)
            i=max(0,bisect.bisect_right(frames,frame)-1)
            # Readback proof uses exact authored keys/first frame. Intermediate
            # preview uses linear position/normalized quaternion interpolation.
            if i+1<len(keys) and frames[i]!=frame:
                alpha=(frame-frames[i])/(frames[i+1]-frames[i]);a=keys[i];b=keys[i+1]
                if dim==4 and np.dot(a,b)<0:b=-b
                value=a*(1-alpha)+b*alpha
            else:value=keys[i]
            values.append(value)
        pos,rot,scale=values;m=quaternion_matrix(rot)@np.diag([*scale,1]);m[:3,3]=pos
        if node['parent']>=0:m=output[node['parent']]@m
        output.append(m)
    return output

def face_normals(vertices,faces):
    normals=np.zeros_like(vertices)
    for face in faces:
        a,b,c=vertices[face];normal=np.cross(b-a,c-a)
        for vertex in face:normals[vertex]+=normal
    lengths=np.linalg.norm(normals,axis=1);normals/=np.maximum(lengths,1e-20)[:,None]
    return normals

def morph_skin(data:bytes,bone_factor_map:dict[str,tuple[float,float,float]]):
    """Return new bytes/report, deforming named influences about their own pivot.

    factors are local xyz multipliers, not object transforms. Runtime collider
    parameters, rig points and all translation/rotation/scale tracks are intact.
    """
    nodes=parse(data);bind=worlds(data,nodes);out=bytearray(data);changed=[]
    factors={n['index']:np.asarray(bone_factor_map[n['name']],dtype=float)
             for n in nodes if n['name'] in bone_factor_map}
    assert factors and all(np.isfinite(f).all() and (f>0).all() for f in factors.values())
    for node in nodes:
        if node['type']!=2 or not node['nv']:continue
        skin=node['pointers'][10];positions=node['pointers'][8];normal_ptr=node['pointers'][9]
        assert skin and positions and normal_ptr
        old_vertices=np.array([F(data,positions+i*12,3) for i in range(node['nv'])])
        vertices=old_vertices.copy();inverse=np.linalg.inv(bind[node['index']]);touched=0
        for i in range(node['nv']):
            at=skin+i*36;a,b,*values=struct.unpack_from('<HH8f',data,at)
            va=np.array(values[:3]);vb=np.array(values[3:6]);wa,wb=values[6:]
            assert a<len(nodes) and b<len(nodes) and abs(wa+wb-1)<1e-3
            original_world=(bind[a]@np.array([*va,1]))*wa+(bind[b]@np.array([*vb,1]))*wb
            hit=False
            if a in factors and wa>0:va*=factors[a];hit=True
            if b in factors and wb>0:vb*=factors[b];hit=True
            if not hit:continue
            world=(bind[a]@np.array([*va,1]))*wa+(bind[b]@np.array([*vb,1]))*wb
            # The separate vertex cache can be the export bind pose rather
            # than animation key0. Apply only the shape delta to that cache.
            vertices[i]=old_vertices[i]+(inverse@(world-original_world))[:3]
            struct.pack_into('<6f',out,at+4,*va,*vb)
            struct.pack_into('<3f',out,positions+i*12,*vertices[i]);touched+=1
        if not touched:continue
        faces=np.frombuffer(data,dtype='<u2',count=node['nf']*3,offset=node['pointers'][4]).reshape(-1,3)
        normals=face_normals(vertices,faces)
        # Preserve original normal magnitudes/orientation rather than replacing
        # authored smoothness: apply the small triangle-normal delta only.
        original_geom_normals=face_normals(old_vertices,faces)
        original_normals=np.array([F(data,normal_ptr+i*12,3) for i in range(node['nv'])])
        corrected=original_normals+(normals-original_geom_normals)
        corrected/=np.maximum(np.linalg.norm(corrected,axis=1),1e-20)[:,None]
        for i,v in enumerate(corrected):struct.pack_into('<3f',out,normal_ptr+i*12,*v)
        struct.pack_into('<6f',out,node['offset']+80,*vertices.min(axis=0),*vertices.max(axis=0))
        changed.append(dict(node=node['name'],vertices=touched,max_displacement=float(np.linalg.norm(vertices-old_vertices,axis=1).max())))
    # The original robot also uses rigid visible pieces parented directly to
    # Head/Spine. Morph those pieces about that exact original joint; hands and
    # feet have other parents and remain byte-identical.
    for node in nodes:
        if node['type']!=1 or node['parent'] not in factors or not node['nv']:continue
        if any(word in node['name'].lower() for word in ['gwizdek','moneta']):continue
        pointer=node['pointers'][8];normal_ptr=node['pointers'][9]
        old_vertices=np.array([F(data,pointer+i*12,3) for i in range(node['nv'])])
        parent=node['parent'];to_parent=np.linalg.inv(bind[parent])@bind[node['index']]
        from_parent=np.linalg.inv(bind[node['index']])@bind[parent]
        parent_vertices=(to_parent@np.column_stack((old_vertices,np.ones(node['nv']))).T).T
        parent_vertices[:,:3]*=factors[parent]
        vertices=(from_parent@parent_vertices.T).T[:,:3]
        faces=np.frombuffer(data,dtype='<u2',count=node['nf']*3,offset=node['pointers'][4]).reshape(-1,3)
        delta=face_normals(vertices,faces)-face_normals(old_vertices,faces)
        normals=np.array([F(data,normal_ptr+i*12,3) for i in range(node['nv'])])+delta
        normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-20)[:,None]
        for i in range(node['nv']):
            struct.pack_into('<3f',out,pointer+i*12,*vertices[i])
            struct.pack_into('<3f',out,normal_ptr+i*12,*normals[i])
        struct.pack_into('<6f',out,node['offset']+80,*vertices.min(axis=0),*vertices.max(axis=0))
        changed.append(dict(node=node['name'],rigid=True,vertices=node['nv'],max_displacement=float(np.linalg.norm(vertices-old_vertices,axis=1).max())))
    assert changed
    # Confirm byte-for-byte invariant streams, not merely decoded key counts.
    for node in nodes:
        for pointer in node['pointers'][:3]:
            if pointer:
                count,kind,start=U(data,pointer+4),U(data,pointer+8),U(data,pointer+12)
                dim=4 if pointer==node['pointers'][1] else 3
                end=start+count*{1:24+12*dim,2:4+12*dim,3:4+4*dim}[kind]
                assert out[pointer:end]==data[pointer:end]
        for pointer_index,length in [(4,node['nf']*6),(5,node['nf']*2),(6,node['nf']*6),(7,U(data,node['offset']+64)*8)]:
            pointer=node['pointers'][pointer_index]
            if pointer:assert out[pointer:pointer+length]==data[pointer:pointer+length]
        if node['type']==2:
            for i in range(node['nv']):
                at=node['pointers'][10]+i*36
                assert out[at:at+4]==data[at:at+4] and out[at+28:at+36]==data[at+28:at+36]
    result=bytes(out);assert len(result)==len(data) and len(parse(result))==len(nodes)
    return result,dict(changed=changed,bytes=len(result),sha256=hashlib.sha256(result).hexdigest(),
        animation_tracks_identical=True,topology_uv_materials_identical=True,bone_ids_weights_identical=True)
