# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json,hashlib,runpy
R=pathlib.Path(__file__).parent;sys.path.insert(0,str(R.parent.parent/'tools/python'))
from PIL import Image,ImageDraw
runpy.run_path(str(R/'check_witcher_atlas.py'))
before={p['path']:p for p in json.loads((R/'frozen-asset-hashes.json').read_text())}
runpy.run_path(str(R/'freeze_handoff.py'))
after={p['path']:p for p in json.loads((R/'frozen-asset-hashes.json').read_text())};changed=[p for p in after if after[p]['sha256']!=before[p]['sha256']]
assert {pathlib.Path(p).name for p in changed}=={'cx_w3_'+n+'.3da' for n in ['geralt','ciri','yennefer','triss','keira','avallach','zoltan']},changed
m=json.loads((R/'faction-manifest.json').read_text());inventory=[];witcher=[];portrait_sheet=Image.new('RGB',(1200,1260),(45,45,45));sheet_draw=ImageDraw.Draw(portrait_sheet)
for team in m['teams']:
 for p in team['players']:
  mesh=pathlib.Path(p['mesh_source']);item=dict(team_id=team['team_id'],stem=p['stem'],mesh_sha256=p['sha256'],images=[])
  for frame,view in [(0,'front'),(0,'side'),(275,'front'),(275,'side')]:
   f=R/f"{p['stem']}-native-{frame}-{view}.png";im=Image.open(f);im.load();item['images'].append(dict(path=str(f),frame=frame,view=view,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,size=im.size))
   if team['team_id']==33:assert f.stat().st_mtime>=mesh.stat().st_mtime,(f,'stale render')
  inventory.append(item)
  if team['team_id']!=33:continue
  sheet=Image.new('RGB',(1000,1040),(45,45,45));draw=ImageDraw.Draw(sheet)
  for i,record in enumerate(item['images']):
   sheet.paste(Image.open(record['path']).resize((500,500)),((i%2)*500,(i//2)*520+20));draw.text(((i%2)*500+10,(i//2)*520+3),f"{p['name']} frame{record['frame']} {record['view']}",fill='white')
  sheet.save(R/(p['stem']+'-fresh-fourviews.jpg'),quality=94)
  item=dict(item);item['portraits']=[]
  for frame in [0,275]:
   f=R/f"{p['stem']}-native-{frame}-front-portrait.png";im=Image.open(f);im.load();assert f.stat().st_mtime>=mesh.stat().st_mtime;item['portraits'].append(dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,size=im.size,frame=frame))
   if frame==0:
    index=len(witcher);portrait_sheet.paste(im.resize((400,400)),((index%3)*400,(index//3)*420+20));sheet_draw.text(((index%3)*400+10,(index//3)*420+4),p['name'],fill='white')
  witcher.append(item)
(R/'all-render-evidence.json').write_text(json.dumps(inventory,indent=2));(R/'witcher-face-fixes-evidence.json').write_text(json.dumps(dict(changed_assets=changed,characters=witcher),indent=2));portrait_sheet.save(R/'witcher-faces-contact-sheet.jpg',quality=95)
print('Frozen28 native assets; decoded112 whole-body images and14 fresh Witcher portraits. Changed only7 Witcher native meshes.',flush=True)
