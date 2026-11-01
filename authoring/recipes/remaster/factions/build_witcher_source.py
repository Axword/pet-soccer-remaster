"""CDPR original character meshes from credited public author ports, through SourceIO.
Geometry/texture only. Workshop Lua/commands are never extracted or executed.
"""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,os,importlib.util,traceback,json,math,re,collections
import bpy,numpy as np
from mathutils import Matrix,Vector
R=pathlib.Path(__file__).parent;P=R.parent.parent;SIO=R/'sources/sourceio/SourceIO-master';os.environ['NO_BPY']='1';sys.path.insert(0,str(P/'tools/python'));sys.path.insert(0,str(R))
from PIL import Image
spec=importlib.util.spec_from_file_location('SourceIO',SIO/'__init__.py',submodule_search_locations=[str(SIO)]);module=importlib.util.module_from_spec(spec);sys.modules['SourceIO']=module;spec.loader.exec_module(module)
from SourceIO.blender_bindings.models.mdl49 import import_mdl49
from SourceIO.blender_bindings.models.materials import get_model_material_names
from SourceIO.blender_bindings.operators.import_settings_base import ModelOptions
from SourceIO.library.shared.content_manager import ContentManager
from SourceIO.library.shared.content_manager.providers.loose_files import LooseFilesContentProvider
from SourceIO.library.utils import FileBuffer,TinyPath
from SourceIO.library.source1.vtf import load_texture
from export_skinned_character import export_skin
OUT=R/'pack'
DEFS=[('Root',0,-1),('Pelvis',2,0),('Spine',3,1),('Neck',40,2),('Head',43,3),('LClav',53,2),('LArm',54,5),('LFore',55,6),('LHand',56,7),('RClav',74,2),('RArm',75,9),('RFore',76,10),('RHand',77,11),('LThigh',4,1),('LCalf',5,13),('LFoot',6,14),('RThigh',22,1),('RCalf',23,16),('RFoot',24,17)]
NATIVE=['ValveBiped.Bip01_Pelvis','ValveBiped.Bip01_Pelvis','ValveBiped.Bip01_Spine2','ValveBiped.Bip01_Neck1','ValveBiped.Bip01_Head1','ValveBiped.Bip01_L_Clavicle','ValveBiped.Bip01_L_UpperArm','ValveBiped.Bip01_L_Forearm','ValveBiped.Bip01_L_Hand','ValveBiped.Bip01_R_Clavicle','ValveBiped.Bip01_R_UpperArm','ValveBiped.Bip01_R_Forearm','ValveBiped.Bip01_R_Hand','ValveBiped.Bip01_L_Thigh','ValveBiped.Bip01_L_Calf','ValveBiped.Bip01_L_Foot','ValveBiped.Bip01_R_Thigh','ValveBiped.Bip01_R_Calf','ValveBiped.Bip01_R_Foot']
SQUAD={'geralt':('904208280','models/player/tfa_w3_geralt_default.mdl',58),'ciri':('1365759533','models/konnie/witcher3/cirialt.mdl',55),'yennefer':('1366624470','models/konnie/witcher3/yenneferalt.mdl',55),'triss':('505431747','models/player/ratedr4ryan/triss_tw3.mdl',54),'keira':('1436344300','models/konnie/witcher3/keira.mdl',54),'avallach':('1369258907','models/konnie/witcher3/avallach.mdl',60),'zoltan':('1434761807','models/konnie/witcher3/zoltan.mdl',40)}
def build(name):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 ws,path,height=SQUAD[name];root=R/'sources/witcher-workshop'/ws;cm=ContentManager();cm.children.clear();cm._cache.clear();cm._exists_cache.clear();cm._owner_cache.clear();cm.add_child(LooseFilesContentProvider(TinyPath(root)))
 options=ModelOptions.default();options.scale=1.;options.import_textures=False;options.import_animations=False;options.import_physics=False;options.create_flex_drivers=False;options.bodygroup_vis_switches=False;options.generate_wrinkle_map_node_group=False
 container=import_mdl49(TinyPath(path),FileBuffer(str(root/path)),cm,options);arm=container.armature;allbones=arm.data.bones
 chosen=[]
 for label,objs in container.bodygroups.items():
  if any(s in label.lower() for s in ['sword','scabbard','weapon']) and name not in ['geralt','ciri']:continue
  # First option is the original port's default appearance; sword remains on back.
  obj=objs[0] if objs else None
  if obj:chosen.append(obj)
 if not chosen:raise RuntimeError('No visible default bodygroups: '+name)
 print('W3SOURCE',name,'bodygroups',[(k,[o.name if o else None for o in v]) for k,v in container.bodygroups.items()],flush=True)
 lookup={label:k for k,label in enumerate(NATIVE) if k!=0}
 def group(label):
  if label in lookup:return lookup[label]
  bone=allbones.get(label)
  return group(bone.parent.name) if bone and bone.parent else 1
 # Atlas all used diffuse maps. Use true alpha only for alpha-tested hair/lashes.
 paths=get_model_material_names(cm,container.mdl);used=[]
 for obj in chosen:
  for mat in obj.data.materials:
   if mat and mat.name not in used:used.append(mat.name)
 atlas=Image.new('RGBA',(2048,2048),(80,70,60,255));regions={};material_sources={};grid=math.ceil(math.sqrt(len(used)));cell=2048//grid
 for idx,label in enumerate(used):
  matkey=next((k for k,p in paths.items() if p==label),label.split('.')[-1] if label.startswith('models/') else label)
  rel=bpy.data.materials[label].get('full_path',paths.get(matkey,label));vmt=(root/'materials'/(rel+'.vmt'))
  if not vmt.exists():
   matches=[p for p in root.glob('materials/**/*.vmt') if p.stem.lower()==matkey.lower()]
   if not matches:raise FileNotFoundError((name,label,rel))
   vmt=matches[0]
  text=vmt.read_text(errors='replace');m=re.search(r'["\']?\$basetexture["\']?\s+["\']?([^"\'\s]+)',text,re.I)
  if not m:m=re.search(r'["\']?\$iris["\']?\s+["\']?([^"\'\s]+)',text,re.I)
  if not m:raise ValueError('No diffuse map '+str(vmt))
  texpath=root/'materials'/(m.group(1).replace('\\','/')+'.vtf')
  if not texpath.exists():
   candidates=list((R/'sources/witcher-workshop').glob('*/materials/**/'+texpath.name))
   if candidates:texpath=candidates[0]
   elif texpath.stem=='mouth_d':texpath=R/'sources/witcher-workshop/1365759533/materials/models/witcher3/cirialt/mouth.vtf'
  rgba,h,w=load_texture(FileBuffer(str(texpath)));assert rgba is not None
  # Decoder pixels map directly to PNG top-down; validated against Ciri's face.
  im=Image.fromarray(np.clip(rgba*255,0,255).astype('uint8'),'RGBA')
  alpha=bool(re.search(r'\$(?:alphatest|translucent)["\']?\s+["\']?1',text,re.I))
  if not alpha:im.putalpha(255)
  size=cell-2;x=idx%grid*cell+1;y=idx//grid*cell+1;im=im.resize((size,size),Image.Resampling.LANCZOS);atlas.paste(im,(x,y));regions[label]=(x,y,size,size);material_sources[label]=dict(vmt=str(vmt),texture=str(texpath),alpha_test=alpha,atlas_region=[x,y,size,size])
  im.save(R/(name+'-material-'+str(idx)+'.png'))
 # Source port is Blender Z-up, facing -Y. Convert to Y-up facing -Z;
 # native exporter applies the accepted +Z-facing root rotation.
 orient=Matrix(((-1,0,0),(0,0,1),(0,1,0)))
 verts=[];normals=[];uv=[];weights=[];faces=[];face_labels=[];uv_repeat_triangles=0;uv_split_triangles=0
 def interpolate(a,b,t):
  return dict(p=a['p'].lerp(b['p'],t),n=a['n'].lerp(b['n'],t),uv=a['uv'].lerp(b['uv'],t),weights={k:a['weights'].get(k,0)*(1-t)+b['weights'].get(k,0)*t for k in a['weights'].keys()|b['weights'].keys()})
 def clip(poly,axis,edge,keep_above):
  result=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   av=a['uv'][axis]-edge;bv=b['uv'][axis]-edge;inside_a=av>=-1e-8 if keep_above else av<=1e-8;inside_b=bv>=-1e-8 if keep_above else bv<=1e-8
   if inside_a:result.append(a)
   if inside_a!=inside_b:result.append(interpolate(a,b,av/(av-bv)))
  return result
 for obj in chosen:
  me=obj.data;me.calc_loop_triangles();groupmap={g.index:group(g.name) for g in obj.vertex_groups}
  for tri in me.loop_triangles:
   label=me.materials[tri.material_index].name;ox,oy,tw,th=regions[label];poly=[]
   for li in tri.loops:
    v=me.vertices[me.loops[li].vertex_index];p=orient@(obj.matrix_world@v.co);n=(orient@obj.matrix_world.to_3x3()@v.normal).normalized();u,vv=me.uv_layers[0].data[li].uv;ww=collections.defaultdict(float)
    for g in v.groups:
     if g.weight>0:ww[groupmap[g.group]]+=g.weight
    if not sum(ww.values()):ww[1]=1
    poly.append(dict(p=p,n=n,uv=Vector((u,vv)),weights=dict(ww)))
   if any(any(q<0 or q>1 for q in v['uv']) for v in poly):uv_repeat_triangles+=1
   # Source ports legitimately place UV islands in repeated tiles, including
   # Ciri's face in(-16,17). Preserve repeat semantics. Split at tile boundaries
   # before packing so interpolation never travels through another atlas cell.
   lo=[math.floor(min(v['uv'][k] for v in poly)) for k in range(2)];hi=[max(lo[k],math.ceil(max(v['uv'][k] for v in poly))-1) for k in range(2)];emitted=0
   for tu in range(lo[0],hi[0]+1):
    for tv in range(lo[1],hi[1]+1):
     piece=poly
     for axis,edge,above in [(0,tu,True),(0,tu+1,False),(1,tv,True),(1,tv+1,False)]:piece=clip(piece,axis,edge,above) if piece else []
     if len(piece)<3:continue
     for corner in range(1,len(piece)-1):
      triangle=[piece[0],piece[corner],piece[corner+1]]
      if (triangle[1]['p']-triangle[0]['p']).cross(triangle[2]['p']-triangle[0]['p']).length<1e-10:continue
      f=[]
      for v in triangle:
       u=min(1,max(0,v['uv'].x-tu));vv=min(1,max(0,v['uv'].y-tv));g=sorted(v['weights'].items(),key=lambda q:q[1],reverse=True)[:2];total=sum(w for _,w in g);f.append(len(verts));verts.append(list(v['p']));normals.append(list(v['n'].normalized()));uv.append(((ox+u*tw)/2048,1-(oy+(1-vv)*th)/2048));weights.append([(k,w/total) for k,w in g])
      faces.append(f);face_labels.append(label);emitted+=1
   if emitted>1:uv_split_triangles+=1
 # Uniform height only affects render mesh. Original gameplay collision is untouched.
 ground=min(v[1] for v,ww in zip(verts,weights) if any(k in [15,18] and w>.1 for k,w in ww));top=max(v[1] for v,ww in zip(verts,weights) if any(k==4 and w>.1 for k,w in ww));factor=height/(top-ground)
 norm=lambda v:[v[0]*factor,(v[1]-ground)*factor,v[2]*factor]
 verts=[norm(v) for v in verts];bones=[dict(name=n,native=b,parent=p,pivot=norm(orient@(arm.matrix_world@allbones[label].matrix_local.translation))) for (n,b,p),label in zip(DEFS,NATIVE)];bones[0]['pivot']=[0,0,0]
 # Weld attribute-identical loop vertices before decimation to retain connected limbs.
 remap={};vv=[];nn=[];uu=[];ww=[];ff=[]
 for f in faces:
  nf=[]
  for i in f:
   key=tuple(round(q,6) for q in verts[i])+tuple(round(q,6) for q in uv[i])+tuple((k,round(w,6)) for k,w in weights[i])
   if key not in remap:remap[key]=len(vv);vv.append(verts[i]);nn.append(normals[i]);uu.append(uv[i]);ww.append(weights[i])
   nf.append(remap[key])
  ff.append(nf)
 verts,normals,uv,weights,faces=vv,nn,uu,ww,ff
 face_fix=None
 if len(faces)>6500:
  # A global error-only collapse starves the smooth face while leaving many
  # hair-card edges. Preserve every original facial triangle; simplify each
  # other material separately so a face can never cross an atlas boundary.
  source_counts=collections.Counter(face_labels)
  protected={label for label in source_counts if any(t in label.lower() for t in ['head','face','eye','mouth','teeth'])}
  hair={label for label in source_counts if any(t in label.lower() for t in ['hair','beard']) and label not in protected}
  face_count=sum(source_counts[label] for label in protected);hair_count=sum(source_counts[label] for label in hair);body_count=len(faces)-face_count-hair_count
  hair_budget=min(2500,hair_count);body_budget=max(1000,15000-face_count-hair_budget)
  partitions=collections.defaultdict(list)
  for f,label in zip(faces,face_labels):partitions[label].append(f)
  original_verts,original_normals,original_uv,original_weights=verts,normals,uv,weights
  verts=[];normals=[];uv=[];weights=[];faces=[];output_counts={}
  for label,part in partitions.items():
   rx,ry,rw,rh=regions[label];ulo,uhi=rx/2048,(rx+rw)/2048;vlo,vhi=1-(ry+rh)/2048,1-ry/2048
   target=len(part) if label in protected else max(4,round(len(part)*(hair_budget/max(1,hair_count) if label in hair else body_budget/max(1,body_count))))
   start_faces=len(faces)
   if target>=len(part):
    for tri in part:
     f=[]
     for i in tri:f.append(len(verts));verts.append(original_verts[i]);normals.append(original_normals[i]);uv.append(original_uv[i]);weights.append(original_weights[i])
     faces.append(f)
   else:
    used=sorted({i for f in part for i in f});local={i:k for k,i in enumerate(used)};me=bpy.data.meshes.new(name+'_'+label+'_lod');me.from_pydata([original_verts[i] for i in used],[],[[local[i] for i in f] for f in part]);ob=bpy.data.objects.new(name+'_'+label+'_lod',me);bpy.context.collection.objects.link(ob);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;layer=me.uv_layers.new()
    for poly in me.polygons:
     for li in poly.loop_indices:layer.data[li].uv=original_uv[used[me.loops[li].vertex_index]]
    for k in range(19):ob.vertex_groups.new(name=str(k))
    for i,old in enumerate(used):
     for k,w in original_weights[old]:ob.vertex_groups[k].add([i],w,'REPLACE')
    dec=ob.modifiers.new('Body and hair LOD; facial topology protected','DECIMATE');dec.ratio=target/len(part);bpy.ops.object.modifier_apply(modifier=dec.name);me=ob.data;me.calc_loop_triangles()
    for tri in me.loop_triangles:
     f=[]
     for li in tri.loops:
      v=me.vertices[me.loops[li].vertex_index];f.append(len(verts));verts.append(list(v.co));normals.append(list(v.normal));u,vv=me.uv_layers.active.data[li].uv;uv.append([min(uhi,max(ulo,u)),min(vhi,max(vlo,vv))]);g=sorted([(q.group,q.weight) for q in v.groups],key=lambda q:q[1],reverse=True)[:2];total=sum(w for k,w in g);weights.append([(k,w/total) for k,w in g])
     faces.append(f)
    bpy.data.objects.remove(ob,do_unlink=True)
   output_counts[label]=len(faces)-start_faces
  face_fix=dict(fix='Correct repeated source UV islands and preserve original face, eyes, mouth and lashes; independently simplify each other material; clamp modifier extrapolation to its own atlas rectangle',uv_repeat_source_triangles=uv_repeat_triangles,uv_boundary_split_source_triangles=uv_split_triangles,post_modifier_clamp='Own material atlas rectangle only, after source repeat geometry was split',source_material_triangles=dict(source_counts),output_material_triangles=output_counts,protected_materials=sorted(protected),target_triangles=15000,actual_triangles=len(faces),original_facial_triangles=face_count,gameplay_timing_changed=False,bodygroup_selection_changed=False)
  (R/('cx_w3_'+name+'-cosmetic-fixes.json')).write_text(json.dumps(face_fix,indent=2));print('W3_FACE_PROTECTED',name,face_fix,flush=True)
 stem='cx_w3_'+name;model=dict(vertices=verts,normals=normals,uv=uv,weights=weights,faces=faces,bones=bones);(R/(stem+'-skin-model.json')).write_text(json.dumps(model));(R/(stem+'-provenance.json')).write_text(json.dumps(dict(workshop_id=ws,source_model=str(root/path),materials=material_sources,height=height,source_models='CD Projekt RED originals, credited author port',gameplay_timing_changed=False,facial_geometry_preserved=face_fix),indent=2));atlas.save(OUT/'Data/Textures'/(stem+'.png'));print('WITCHER',name,export_skin(model,stem,OUT),'faces',len(faces),flush=True)
for name in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else SQUAD:
 try:build(name)
 except Exception:traceback.print_exc();raise
