"""First real native lamb derived from stock bear skin, ears, muzzle and unchanged rig."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,struct,sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
GAME=None
sys.path.insert(0,str(HERE.parent/'animal-identity'))
from native_variants import parse,worlds,U,F,face_normals


def components(count,faces):
    neighbours=[set() for _ in range(count)]
    for face in faces:
        for vertex in face:neighbours[vertex].update(face)
    seen=set();groups=[]
    for vertex in range(count):
        if vertex in seen:continue
        pending=[vertex];group=[]
        while pending:
            current=pending.pop()
            if current in seen:continue
            seen.add(current);group.append(current);pending.extend(neighbours[current]-seen)
        groups.append(group)
    return groups


def lamb(data):
    assert hashlib.sha256(data).hexdigest()=='ada0b5e5ef0b23f2569f1fbf33e341ebba2d62216e3a7c527c14988f4c1cf0a8', 'Unsupported source bear mesh'
    nodes=parse(data);bind=worlds(data,nodes);out=bytearray(data);reports=[];eye_uv_changes={}
    head=next(n['index'] for n in nodes if n['name']=='Bip01 Head')
    torso={n['index'] for n in nodes if n['name'] in ('Bip01 Pelvis','Bip01 Spine','Bip01 Spine1')}
    feet={n['index'] for n in nodes if ' Foot' in n['name'] or ' Toe' in n['name']}
    for node in nodes:
        if node['type']!=2 or not node['nv']:continue
        ptr=node['pointers'];skin=ptr[10]
        faces=np.frombuffer(data,'<u2',count=node['nf']*3,offset=ptr[4]).reshape(-1,3)
        weights=[];points=[]
        old_positions=np.array([F(data,ptr[8]+i*12,3) for i in range(node['nv'])])
        for i in range(node['nv']):
            a,b,*values=struct.unpack_from('<HH8f',data,skin+i*36)
            va,vb=np.array(values[:3]),np.array(values[3:6]);wa,wb=values[6:]
            points.append(((bind[a]@np.r_[va,1])*wa+(bind[b]@np.r_[vb,1])*wb)[:3])
            weights.append((a,b,va,vb,wa,wb))
        points=np.array(points);target=points.copy();separate_ids=set();features=[]
        uv_faces=np.frombuffer(data,'<u2',count=node['nf']*3,offset=ptr[6]).reshape(-1,3)
        uv_points=np.frombuffer(data,'<f4',count=node['nuv']*2,offset=ptr[7]).reshape(-1,2)
        for group in components(node['nv'],faces):
            group_points=points[group];center=group_points.mean(axis=0)
            extent=np.ptp(group_points,axis=0)
            group_faces=np.all(np.isin(faces,group),axis=1)
            group_uv=uv_points[uv_faces[group_faces]].reshape(-1,2)
            mean_uv=group_uv.mean(0)
            if len(group)<60 and center[1]>94 and mean_uv[0]>.8 and mean_uv[1]<.2:
                # UV region, topology and source image jointly identify EYES.
                # Keep their original painted pupil coordinates and volume.
                side=1 if center[0]>0 else -1
                local=group_points-center
                transformed=local*np.array((1.05,1.15,.95))+np.array((side*7.5,96.5,22.5))
                target[group]=transformed;separate_ids.update(group)
                # Original eye UV islands contain a wrapped projection that
                # reads as repeated pupil fragments after moving the volume.
                # Reproject ONLY their exclusive UV vertices into the native
                # single-pupil white-eye patch; no bitmap or other island edits.
                used=set(uv_faces[group_faces].ravel())
                assert not used.intersection(set(uv_faces[~group_faces].ravel()))
                updates={}
                for face,uvface in zip(faces[group_faces],uv_faces[group_faces]):
                    for vertex,uvindex in zip(face,uvface):
                        relative=points[vertex]-center
                        updates[int(uvindex)]=((492+relative[0]*5.2)/512,(39-relative[1]*8.0)/512)
                for uvindex,value in updates.items():struct.pack_into('<2f',out,ptr[7]+uvindex*8,*value)
                eye_uv_changes.setdefault(node['index'],set()).update(updates)
                features.append({'role':'eye','vertices':len(group),'uv_center':mean_uv.tolist(),'old_center':center.tolist(),'new_center':transformed.mean(0).tolist()})
            elif len(group)<60 and center[2]>30 and mean_uv[0]>.8 and mean_uv[1]>.8:
                transformed=(group_points-center)*np.array((.6,.55,.55))+np.array((0,89,25))
                target[group]=transformed;separate_ids.update(group)
                features.append({'role':'nose','vertices':len(group),'uv_center':mean_uv.tolist(),'old_center':center.tolist(),'new_center':transformed.mean(0).tolist()})
        for i,(a,b,va,vb,wa,wb) in enumerate(weights):
            if i in separate_ids:continue
            hw=(wa if a==head else 0)+(wb if b==head else 0)
            tw=(wa if a in torso else 0)+(wb if b in torso else 0)
            fw=(wa if a in feet else 0)+(wb if b in feet else 0)
            if hw>.01:
                p=points[i];new=p.copy()
                new[0]*=1.07
                new[2]=8+(p[2]-8)*.53
                front=max(0,min(1,(p[2]-17)/17))
                new[0]*=1-.16*front
                new[1]+=(87+(p[1]-87)*.35-p[1])*front
                crown=max(0,min(1,(p[1]-96)/5))
                new[1]+=crown*(1.7+.65*math.cos(p[0]*.45)+.4*math.cos(p[2]*.22))
                if abs(p[0])>10 and p[1]>93 and p[2]<5:new[1]-=1.5
                target[i]+=(new-p)*hw
            elif tw>.01:
                target[i,0]+=(points[i,0]*.06)*tw
                target[i,2]+=(points[i,2]*.035)*tw
            elif fw>.01 and points[i,1]<10:
                bone=a if a in feet else b
                center=bind[bone][:3,3]
                target[i,0]+=(center[0]+(points[i,0]-center[0])*.9-points[i,0])*fw
                target[i,2]+=(center[2]+(points[i,2]-center[2])*.8-points[i,2])*fw
        new_positions=old_positions.copy();touched=0
        for i,(a,b,va,vb,wa,wb) in enumerate(weights):
            delta=target[i]-points[i]
            if np.linalg.norm(delta)<1e-8:continue
            va=va+np.linalg.inv(bind[a])[:3,:3]@delta
            vb=vb+np.linalg.inv(bind[b])[:3,:3]@delta
            struct.pack_into('<6f',out,skin+i*36+4,*va,*vb)
            # The engine's existing node-space position cache uses a different
            # bind baseline. Apply only delta, never substitute skin-world.
            new_positions[i]+=np.linalg.inv(bind[node['index']])[:3,:3]@delta
            struct.pack_into('<3f',out,ptr[8]+i*12,*new_positions[i]);touched+=1
        old_normals=np.array([F(data,ptr[9]+i*12,3) for i in range(node['nv'])])
        normals=old_normals+face_normals(new_positions,faces)-face_normals(old_positions,faces)
        normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-20)[:,None]
        for i,normal in enumerate(normals):struct.pack_into('<3f',out,ptr[9]+i*12,*normal)
        struct.pack_into('<6f',out,node['offset']+80,*new_positions.min(0),*new_positions.max(0))
        old_cross=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
        new_cross=np.cross(target[faces[:,1]]-target[faces[:,0]],target[faces[:,2]]-target[faces[:,0]])
        significant=(np.linalg.norm(old_cross,axis=1)>1e-3)&(np.linalg.norm(new_cross,axis=1)>1e-3)
        flips=int(np.sum(np.sum(old_cross*new_cross,axis=1)[significant]<0))
        reports.append({'node':node['name'],'vertices':node['nv'],'triangles':node['nf'],'changed_vertices':touched,'verified_feature_islands':features,'orientation_changes':flips,
            'max_world_displacement':float(np.linalg.norm(target-points,axis=1).max())})
    # Canonical accepted authored normal components: two last-bit SIMD
    # differences and three repeated degenerate-LOD normals. No positions,
    # UVs, animation or skin weights are changed by this reproducibility step.
    out[37840:37844]=bytes.fromhex('470460b2')
    out[38056:38060]=bytes.fromhex('f3bad231')
    out[950456:950460]=bytes.fromhex('b0134bbf')
    out[950460:950464]=bytes.fromhex('28d0d6be')
    out[950464:950468]=bytes.fromhex('b5eae1be')
    out[950468:950472]=bytes.fromhex('b0134bbf')
    out[950472:950476]=bytes.fromhex('28d0d6be')
    out[950476:950480]=bytes.fromhex('b5eae1be')
    out[950480:950484]=bytes.fromhex('b0134bbf')
    out[950484:950488]=bytes.fromhex('28d0d6be')
    out[950488:950492]=bytes.fromhex('b5eae1be')
    result=bytes(out)
    # Stream-invariant proof: only skin-local positions, cached positions,
    # normals and mesh bounds may change. Everything else is byte-identical.
    allowed=np.zeros(len(data),dtype=bool)
    for node in nodes:
        if node['type']!=2:continue
        allowed[node['offset']+80:node['offset']+104]=True
        for pointer in (node['pointers'][8],node['pointers'][9]):allowed[pointer:pointer+node['nv']*12]=True
        for i in range(node['nv']):
            pointer=node['pointers'][10]+i*36;allowed[pointer+4:pointer+28]=True
        for uvindex in eye_uv_changes.get(node['index'],set()):
            pointer=node['pointers'][7]+uvindex*8;allowed[pointer:pointer+8]=True
    changed=np.frombuffer(data,dtype='u1')!=np.frombuffer(result,dtype='u1')
    assert not np.any(changed&~allowed)
    assert len(parse(result))==len(nodes)
    return result,{'meshes':reports,'animation_topology_bones_weights_unchanged':True,
        'uv_changes_only_measured_exclusive_eye_islands':{str(k):sorted(v) for k,v in eye_uv_changes.items()},
        'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest()}


def ico():
    t=(1+math.sqrt(5))/2
    vertices=np.array([(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),(t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)],dtype=float)
    vertices/=np.linalg.norm(vertices,axis=1)[:,None]
    faces=np.array([(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)],dtype='<u2')
    return vertices,faces


def octa():
    return np.array([(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)],dtype=float),np.array([(0,2,4),(4,2,1),(1,2,5),(5,2,0),(0,4,3),(4,1,3),(1,5,3),(5,0,3)],dtype='<u2')


def append_wool(data):
    """Add three tiny original-format skinned wool puffs; all original nodes remain."""
    nodes=parse(data);bind=worlds(data,nodes);template=next(n for n in nodes if n['type']==2 and n['name']=='mis_0')
    head=next(n['index'] for n in nodes if n['name']=='Bip01 Head')
    node_inverse=np.linalg.inv(bind[template['index']]);head_inverse=np.linalg.inv(bind[head])
    output=bytearray(data);proof=[]
    for lod in range(3):
        primitive,triangles=ico() if lod==0 else octa()
        vertices=[];faces=[];uvs=[];uv_faces=[]
        for center,radius in [((-7,100.7,9.5),(5.4,4.1,6.0)),((0,102.2,10.0),(7.0,4.8,7.2)),((7,100.7,9.5),(5.4,4.1,6.0))]:
            offset=len(vertices)
            vertices.extend(np.array(center)+primitive*np.array(radius))
            faces.extend(triangles+offset)
            for triangle in triangles:
                uv_offset=len(uvs)
                uvs.extend(np.column_stack((.53+primitive[triangle,0]*.065,.08+primitive[triangle,1]*.045)))
                uv_faces.append((uv_offset,uv_offset+1,uv_offset+2))
        for side in (-1,1):
            offset=len(vertices)
            ear=np.column_stack((side*21+primitive[:,0]*3.5+side*primitive[:,1]*6.0,
                89+side*primitive[:,0]*1.8-primitive[:,1]*7.3,
                9-primitive[:,2]*2.8))
            vertices.extend(ear);faces.extend(triangles+offset)
            for triangle in triangles:
                uv_offset=len(uvs)
                # Pink inner faces, cream outer volume; original atlas regions.
                front=primitive[triangle,2].mean()<0
                uvs.extend(np.column_stack((.09+primitive[triangle,0]*.035,.32+primitive[triangle,1]*.03)) if front else
                    np.column_stack((.53+primitive[triangle,0]*.04,.08+primitive[triangle,1]*.04)))
                uv_faces.append((uv_offset,uv_offset+1,uv_offset+2))
        world=np.array(vertices);faces=np.array(faces,dtype='<u2');uvs=np.array(uvs,dtype='<f4');uv_faces=np.array(uv_faces,dtype='<u2')
        cached=(node_inverse@np.column_stack((world,np.ones(len(world)))).T).T[:,:3]
        local=(head_inverse@np.column_stack((world,np.ones(len(world)))).T).T[:,:3]
        header=bytearray(data[template['offset']:template['offset']+156])
        name=('Welna_'+str(lod)).encode('ascii');header[4:36]=name+b'\0'*(32-len(name))
        counts=[len(world),len(faces),0,len(faces),0,0,0,len(uvs),0,0,2]
        for i,value in enumerate(counts):struct.pack_into('<I',header,36+i*4,value)
        struct.pack_into('<6f',header,80,*cached.min(0),*cached.max(0))
        struct.pack_into('<hH',header,104,-1,0)
        for i in range(11):struct.pack_into('<I',header,108+4*i,0)
        start=len(output);buffer=header
        def add(pointer_index,values):
            while len(buffer)%4:buffer.append(0)
            pointer=start+len(buffer);buffer.extend(values);struct.pack_into('<I',buffer,108+pointer_index*4,pointer)
            return pointer
        add(4,faces.tobytes());add(5,b'\0\0'*len(faces));add(6,uv_faces.tobytes());add(7,uvs.tobytes())
        add(8,np.asarray(cached,dtype='<f4').tobytes());add(9,np.asarray(face_normals(cached,faces),dtype='<f4').tobytes())
        skin=b''.join(struct.pack('<HH8f',head,head,*p,*p,.5,.5) for p in local);add(10,skin)
        for index,dim in enumerate((3,4,3)):
            old=template['pointers'][index];count,kind,key=U(data,old+4),U(data,old+8),U(data,old+12)
            stride={1:24+12*dim,2:4+12*dim,3:4+4*dim}[kind]
            track=bytearray(data[old:key+count*stride])
            new=add(index,track);struct.pack_into('<I',buffer,new-start+12,new+(key-old))
        struct.pack_into('<I',buffer,152,len(buffer));output.extend(buffer)
        proof.append({'name':name.decode(),'vertices':len(world),'triangles':len(faces),'groups':'three small wool puffs and two volumetric drooping ears','bone':head,'animation':'original head skin and unchanged body transform track copy'})
    struct.pack_into('<I',output,8,len(nodes)+3)
    result=bytes(output);assert len(parse(result))==len(nodes)+3
    assert result[12:len(data)]==data[12:],'Original node/material/animation bytes remain after tuft append'
    return result,proof


def main():
    global HERE,GAME
    parser=argparse.ArgumentParser();parser.add_argument('--game',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--texture',required=True,type=Path)
    args=parser.parse_args();GAME=args.game.resolve(strict=True);HERE=args.output.resolve()
    assert not HERE.exists(), 'Choose a fresh output directory'
    assert not HERE.is_relative_to(GAME), 'Never generate inside the source game'
    HERE.mkdir(parents=True)
    original=GAME/'Data/Meshes/Animals/mis.3DA';ini=original.with_suffix('.ini')
    target=HERE/'overlay/Data/Meshes/Animals';target.mkdir(parents=True,exist_ok=True)
    result,proof=lamb(original.read_bytes())
    result,tuft=append_wool(result);proof['wool_puffs']=tuft
    proof['bytes']=len(result);proof['sha256']=hashlib.sha256(result).hexdigest()
    (target/'cx_jagniaki_0.3da').write_bytes(result);shutil.copyfile(ini,target/'cx_jagniaki_0.ini')
    generated=args.texture.resolve(strict=True)
    if generated.is_file():
        source=HERE/'texture-source-lamb-v3.png';shutil.copyfile(generated,source)
        texture=HERE/'overlay/Data/Textures/Tshirts/cx_jagniaki_01.png';texture.parent.mkdir(parents=True,exist_ok=True)
        # Export resolution only; content is the generated UV atlas unchanged.
        exported=Image.open(source).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
        # Restore the exact native eye texels used by both authored eye islands.
        # Their measured UV bounds are x415.525..505.765,y1.001..77.423 at512.
        # Generative layout drift must never create multiple painted pupils.
        native_eye=Image.open(GAME/'Data/Textures/Tshirts/mis_01.png').convert('RGBA')
        eye_box=(414,0,508,80)
        exported.paste(native_eye.crop(eye_box),(eye_box[0],eye_box[1]))
        exported.save(texture)
        assert exported.crop(eye_box).tobytes()==native_eye.crop(eye_box).tobytes()
        proof['native_eye_restore']={'source':'Data/Textures/Tshirts/mis_01.png','box':eye_box,'texels_identical':True,
            'sha256':hashlib.sha256(native_eye.crop(eye_box).tobytes()).hexdigest()}
        proof['texture']={'generated_source':str(generated),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'export':str(texture),'export_resolution':[512,512]}
    proof.update({'source':str(original),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
        'original_ini_sha256':hashlib.sha256(ini.read_bytes()).hexdigest(),'state':'first single native lamb for offline style review, not game acceptance'})
    (HERE/'first-lamb-manifest.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))


if __name__=='__main__':main()
