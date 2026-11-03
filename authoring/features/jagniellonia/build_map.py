"""Podlasie: exact original farm geometry/restart envelope, scoped club barn paint."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sys
from PIL import Image
HERE=Path(__file__).resolve().parent
GAME=None
sys.path.insert(0,str(HERE.parent/'base-maps'));from native_tex import encode_tex,parse_tex


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    global HERE,GAME
    parser=argparse.ArgumentParser();parser.add_argument('--game',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--polish-overlay',required=True,type=Path);parser.add_argument('--barn-texture',required=True,type=Path)
    args=parser.parse_args();GAME=args.game.resolve(strict=True);HERE=args.output.resolve()
    assert not HERE.is_relative_to(GAME), 'Never generate inside the source game'
    assert not (HERE/'overlay/Data/Levels/Podlasie').exists(), 'Map output already exists'
    HERE.mkdir(parents=True,exist_ok=True)
    src=GAME/'Data/Levels/Kurczaki';target=HERE/'overlay/Data/Levels/Podlasie';target.mkdir(parents=True,exist_ok=True)
    visual=args.polish_overlay.resolve(strict=True)/'Data/Levels/Kurczaki'
    records=[]
    for source in sorted(src.rglob('*')):
        if not source.is_file():continue
        rel=source.relative_to(src);newrel=Path(re.sub('kurczaki','Podlasie',str(rel),flags=re.I))
        dst=target/newrel;dst.parent.mkdir(parents=True,exist_ok=True)
        actual=visual/rel if (visual/rel).is_file() else source
        if source.suffix.lower()=='.map':continue
        shutil.copy2(actual,dst)
        records.append({'relative':dst.relative_to(HERE/'overlay').as_posix(),'source':str(actual),'sha256':sha(dst.read_bytes()),'unchanged_source_bytes':True})
    old=(src/'Kurczaki.map').read_bytes();new=old;allowed=set();substitutions=[]
    replacements=[(rb'Kurczaki',b'Podlasie'),(rb'\\stodola\.3DA',b'\\owcznia.3DA')]
    for pattern,replacement in replacements:
        matches=list(re.finditer(pattern,new,re.I));assert matches
        for match in matches:
            assert match.end()-match.start()==len(replacement),'All native MAP string edits must keep byte count'
            allowed.update(range(match.start(),match.end()));substitutions.append({'offset':match.start(),'before':match.group().decode('ascii'),'after':replacement.decode('ascii')})
        new=re.sub(pattern,lambda _:replacement,new,flags=re.I)
    assert len(old)==len(new)==573056
    changed=[i for i,(a,b) in enumerate(zip(old,new)) if a!=b];assert set(changed)<=allowed
    mapfile=target/'Podlasie.map';mapfile.write_bytes(new)
    # Clone the real native farm barn. Only its material filename changes;
    # topology, object bounds, pivot, tracks and collision geometry are identical.
    source=GAME/'Data/Meshes/Objects/stodola.3DA';original=source.read_bytes();barn=bytearray(original)
    assert original[16:48].split(b'\0')[0].lower()==b'stodola.png'
    barn[16:48]=b'cx_jag_barn.png'.ljust(32,b'\0')
    destination=HERE/'overlay/Data/Meshes/Objects/owcznia.3DA';destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(barn)
    assert barn[:16]==original[:16] and barn[48:]==original[48:]
    generated=args.barn_texture.resolve(strict=True)
    sourcecopy=HERE/'texture-source-barn.png';shutil.copyfile(generated,sourcecopy)
    texture=HERE/'overlay/Data/Textures/cx_jag_barn.png';texture.parent.mkdir(parents=True,exist_ok=True)
    image=Image.open(sourcecopy).convert('RGB').resize((512,512),Image.Resampling.LANCZOS);image.save(texture)
    encoded=encode_tex(image,(GAME/'Data/Textures/stodola.tex').read_bytes());texture.with_suffix('.tex').write_bytes(encoded)
    assert parse_tex(encoded)[:2]==(512,512)
    report={'format':'PET-SOCCER-JAGNIELLONIA-MAP-1','id':42,'name':'Podlaska Polana','internal_folder':'Podlasie',
        'source_map':str(src/'Kurczaki.map'),'source_map_sha256':sha(old),'map_sha256':sha(new),'bytes':len(new),
        'only_map_deltas':'equal-length ASCII folder and barn mesh filename spans',
        'changes':substitutions,'all_other_map_bytes_identical':True,'pitch_limits_spawns_heights_collisions_and_restarts_identical':True,
        'copied_dependencies':records,'barn_original_sha256':sha(original),'barn_only_material_filename_changed':True,
        'existing_original_props_preserved':True,'old_map40_kaer_morhen_not_touched':True,'legacy42_backdrop_must_be_disabled':True,
        'native_game_tested':False}
    (HERE/'map-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'map':str(mapfile),'changed_ascii_spans':len(substitutions),'copied_dependencies':len(records),'source_geometry_preserved':True}))


if __name__=='__main__':main()
