"""Build isolated menu/wardrobe fix; never overwrite the input game.

Requires the published GMW beta class methods and a separately compiled
CXTeamColours.class targeting Java1.3. Other archive entries are preserved.
The output directory must differ from the input directory.
"""
from pathlib import Path
import argparse, hashlib, json, re, struct, sys, zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
sys.path.insert(0, str(SOURCE))
from tools.classfile import ClassFile, op, append

EXPECTED = {
 'EAnimals.class': {
  '<clinit>()V':'4644bfbbd538498bb721805d326d4a4771d999db419e15cf7f630530c60a6623',
  'SetAppearance(LMeshObject;III)V':'06b131b55855d442741edadfd84b61930781de2d1eb3652930e021260dab5337',
  'GetClothNormal(II)Ljava/lang/String;':'5c2800cde214b5d2eab2b1cc43bdf0853268fba9f27a698947d26a4ea5bc8a6b',
  'GetClothNormalLogo(II)Ljava/lang/String;':'c603213573994b23f08c2443ba7945e2b44d2bc15ca54fcbab42710f2c8314e6',
  'GetClothesCount(I)I':'4dc1209dd99a4ef802ee3ae1e7d93d732b4dd9700d3be983065275ce547acf0e'},
 'MenuChooseTeamColors.class': {
  'SetColor(I)V':'4c8c8dc4a2b98767b45801aadaffb9794ee496f7a66e604caf2d0e9b7bb01416',
  'SetInfo(LTeamData;I)V':'4db5dc0a7f31df4c8a77c0210ed2f052db9c0c6ce5015d5e860554c2cd61897a',
  'ShowInfo()V':'851467c6e03b2adc52fcd1af1d62093e864bc3da80519670069de21d83dec2fd'},
 'TeamData.class': {
  'SetClothesId(I)V':'9f016b3bad01d29c503481ff58c80ea0800341e79933642b12335c25c4d8b95f'},
 'SoccerMenuShowObjectModule.class': {
  'SetFootballer(II)V':'2e9b4bf121621e174a644367ad3a78d9cec50dbaf5afd5abc0de1eac1446f546',
  'SetFootballerCup(II)V':'db661e0d894224fa944674e86eef348b13ec2e6aeb5d25fbe71a91f9fa4935fe'}
}

def digest(data): return hashlib.sha256(data).hexdigest()
def code(c,name,desc):
    raw=c.code(name,desc)[1]
    return raw[8:8+struct.unpack_from('>I',raw,4)[0]]
def call(c,name,desc): return op(184,c.member('CXTeamColours',name,desc,10))
def field(c,owner,name,desc): return op(180,c.member(owner,name,desc))

def apply(classes, helper):
    assert struct.unpack_from('>H',helper,6)[0] == 47, 'Helper must target Java1.3'
    assert 'CXTeamColours.class' not in classes, 'Already applied; use a fresh input'
    updates={}
    changed=[]
    for filename,methods in EXPECTED.items():
        c=ClassFile(classes[filename])
        for signature,expected in methods.items():
            name,tail=signature.split('(',1);desc='('+tail
            before=code(c,name,desc)
            assert digest(before)==expected, (filename,signature,'Unexpected owned method')
            if filename=='EAnimals.class':
                if name=='<clinit>': after=append(before,call(c,'Init','()V'))
                elif name=='SetAppearance':
                    # A multiple of four preserves the tableswitch alignment.
                    prefix=b'\x1b\x1c'+call(c,'Colour','(II)I')+b'\x3d\0\0'
                    assert len(prefix)==8
                    after=prefix+before
                elif name=='GetClothNormal':
                    after=b'\x1a\x1b'+call(c,'Normal','(II)Ljava/lang/String;')+b'\xb0'
                elif name=='GetClothNormalLogo':
                    after=b'\x1a\x1b'+call(c,'Icon','(II)Ljava/lang/String;')+b'\xb0'
                elif name=='GetClothesCount': after=b'\x1a'+call(c,'Count','(I)I')+b'\xac'
            elif filename=='MenuChooseTeamColors.class':
                if name=='ShowInfo':
                    after=b'\x2a'+call(c,'Prepare','(LMenuChooseTeamColors;)V')+before
                elif name=='SetInfo':
                    after=b'\x2b'+call(c,'Team','(LTeamData;)V')+before
                elif name=='SetColor':
                    after=b'\x2a'+field(c,'MenuChooseTeamColors','m_nAnimal','I')+b'\x1b'+call(c,'Colour','(II)I')+b'\x3c'+before
            elif filename=='TeamData.class':
                after=b'\x2a'+field(c,'TeamData','m_nAnimalType','I')+b'\x1b'+call(c,'Colour','(II)I')+b'\x3c'+before
            elif filename=='SoccerMenuShowObjectModule.class':
                after=b'\x1b\x1c'+call(c,'Colour','(II)I')+b'\x3d\0\0'+before
            c.edit(name,lambda _,a=after:a,desc)
            changed.append({'class':filename,'method':signature,'before_sha256':expected,
                            'after_sha256':digest(after)})
        updates[filename]=c.emit()
    updates['CXTeamColours.class']=helper
    return updates,changed

def fix_menu(data):
    # The original CTC numeric parser requires a leading zero before a decimal.
    return re.sub(rb'(?<=[(,])([ \t]*)(-?)\.(?=\d)',rb'\g<1>\g<2>0.',data)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--code-input',type=Path,help='Optional unpatched archive, e.g. one with club names already changed')
    parser.add_argument('--helper',type=Path,default=SOURCE/'build/java/CXTeamColours.class')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    game=args.game.resolve();out=args.output.resolve()
    assert out!=game and not out.is_relative_to(game), 'Output must be outside the input game'
    out.mkdir(parents=True,exist_ok=True)
    source_code=args.code_input.resolve() if args.code_input else game/'code.pak'
    with zipfile.ZipFile(source_code) as z:
        entries=z.infolist();before={i.filename:z.read(i.filename) for i in entries}
    updates,changed=apply(before,args.helper.read_bytes())
    after=dict(before);after.update(updates)
    with zipfile.ZipFile(out/'code.pak','w') as z:
        for info in entries: z.writestr(info,after[info.filename])
        for name in sorted(set(after)-set(before)):
            info=zipfile.ZipInfo(name,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,after[name])
    assert all(before[n]==after[n] for n in before if n not in updates)
    info=(game/'code_inf.pak').read_bytes()
    if b'CXTeamColours.class' not in info.splitlines():
        info=info.rstrip(b'\r\n')+b'\r\nCXTeamColours.class\r\n'
    (out/'code_inf.pak').write_bytes(info)
    menu=[]
    for suffix in ('','640','1024'):
        rel=Path('Data/Menu/scr')/('Multiplayer'+suffix+'.scr')
        data=(game/rel).read_bytes();fixed=fix_menu(data)
        assert fixed.count(b'LogicSize(0.95,')==1 and fixed.count(b'LogicPos(0.025,')==1
        assert not re.search(rb'[(,]\s*-?\.\d',fixed)
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(fixed)
        menu.append({'path':rel.as_posix(),'before_sha256':digest(data),'after_sha256':digest(fixed)})
    manifest={'input_game':str(game),'before_code_sha256':digest(source_code.read_bytes()),
              'after_code_sha256':digest((out/'code.pak').read_bytes()),
              'methods':changed,'menus':menu,'other_archive_entries_unchanged':True,
              'original_team_outfits_unchanged':True,'custom_species':list(range(37,58)),
              'custom_outfits':1,'runtime_test_required':True}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(manifest,ensure_ascii=True))

if __name__=='__main__': main()
