# Development recipe: require an isolated copy made by tools/prepare_authoring.py.
import os as _authoring_os, pathlib as _authoring_pathlib
_authoring_workspace = _authoring_os.environ.get('PETSOCCER_AUTHORING_WORKSPACE')
if not _authoring_workspace or not _authoring_pathlib.Path(__file__).resolve().is_relative_to(_authoring_pathlib.Path(_authoring_workspace).resolve()):
    raise RuntimeError('Prepare an isolated authoring workspace first; do not run recipes from the repository or installed game.')
import pathlib,sys,json
R=pathlib.Path(__file__).parent;P=R.parents[3];sys.path.insert(0,str(P/'tools/python'));from zenkit import DaedalusScript
s=DaedalusScript.load(pathlib.Path(str(_authoring_pathlib.Path(_authoring_os.environ['GOTHIC_GAME_DIR']) / '_work/Data/scripts/_compiled/Gothic.dat')))
def rows(symbol):
 pc=symbol.address;out=[]
 for _ in range(2000):
  i=s.get_instruction(pc);r=dict(op=i.op.name,arg=i.immediate)
  if i.op.name in ['PUSHV','PUSHVI','BE','BL']:
   q=s.get_symbol_by_index(i.symbol) if i.op.name!='BL' else s.get_symbol_by_address(i.address)
   if q:
    r['symbol']=q.name
    if q.type.name=='STRING' and not q.is_member:
     try:r['string']=q.get_string()
     except:pass
  elif i.op.name=='PUSHI' and i.immediate>0:
   q=s.get_symbol_by_index(i.immediate)
   if q:r['constant_symbol']=q.name
  out.append(r);pc+=i.size
  if i.op.name=='RSR':break
 return out
targets=['INFO_BAU_4_WASSER','DIA_ROSCOE_COMEAGAIN','DIA_MUD_GETLOST']+[q.name for q in s.symbols if q.type.name=='INSTANCE' and 'ROSCOE' in q.name and not q.name.startswith('DIA_')]
out={}
for n in targets:
 q=s.get_symbol_by_name(n)
 if q:out[n]=rows(q);print(n,json.dumps(out[n]),flush=True)
(R/'npc-extra-definitions.json').write_text(json.dumps(out,indent=2))
