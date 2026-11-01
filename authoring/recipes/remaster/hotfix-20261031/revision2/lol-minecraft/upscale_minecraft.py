"""Pixel-preserving Minecraft texture enlargement; no generated detail."""
# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,hashlib
D=pathlib.Path(__file__).resolve().parent;P=D.parents[3]
sys.path.insert(0,str(P/'tools/python'))
from PIL import Image
rows=[]
for stem in ['steve','cx_mc_steve','cx_mc_alex','cx_mc_zombie','cx_mc_skeleton','cx_mc_creeper','cx_mc_enderman','cx_mc_villager']:
 rel=pathlib.Path('Data/Textures')/(stem+'.png');src=P/'Remaster-Pack'/rel
 if not src.exists():src=P/'PetSoccer-Remaster-Test'/rel
 with Image.open(src) as img:
  img=img.convert('RGBA');ratio=2048//img.width;assert ratio>=1 and ratio&(ratio-1)==0
  output=img.resize((img.width*ratio,img.height*ratio),Image.Resampling.NEAREST)
  assert output.resize(img.size,Image.Resampling.NEAREST).tobytes()==img.tobytes()
  # Every source pixel is now a constant ratio×ratio block, including alpha.
  target=D/'Pack'/rel;target.parent.mkdir(parents=True,exist_ok=True);output.save(target)
  row={'relative':str(rel),'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_dimensions':img.size,'output_dimensions':output.size,'integer_nearest_scale':ratio,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'original_RGBA_exact_on_downsample':True,'invented_pixels':False,'max_world_edge_blur_vs_previous':1/ratio}
  rows.append(row);print(stem,img.size,'->',output.size)
(D/'minecraft-manifest.json').write_text(json.dumps(rows,indent=2))
