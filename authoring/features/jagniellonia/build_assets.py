"""Build the seven approved native lamb identities and bounded native texture caches."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sys
from PIL import Image
HERE=Path(__file__).resolve().parent
GAME=None
sys.path.insert(0,str(HERE.parent/'animal-identity'));from native_variants import morph_skin,parse
sys.path.insert(0,str(HERE.parent/'base-maps'));from native_tex import encode_tex,parse_tex,decode_level
GENERATED=None
KITS={number:'kit-'+number+'.png' for number in ('02','03','04','05')}
MODULE=HERE
sys.path.insert(0,str(MODULE.parent/'eyes-fix'));from build_eye_delta import fix as fix_eyes
PROFILES=[((1,1,1),1),((1.025,1.02,.98),1.015),((.985,1.035,1.015),.99),
    ((1.03,.985,1.02),1.025),((1.015,1.025,.975),1.00),((.98,.985,1.035),.985),((1.01,1.04,1.00),1.02)]


def build_icons():
    """Retain real original jersey sprite geometry/alpha/shading; native palette edits only."""
    import numpy as np
    source=Image.open(GAME/'Data/Menu/TShirtsIcons/misie01.png').convert('RGBA');pixels=np.asarray(source).copy();rgb=pixels[:,:,:3].astype(float)
    mask=(rgb[:,:,0]>28)&(rgb[:,:,0]>rgb[:,:,1]*1.4+5)&(rgb[:,:,0]>rgb[:,:,2]*1.4+5)&(pixels[:,:,3]>0)
    intensity=np.clip(rgb[:,:,0]/240,0,1.08);x=np.indices(mask.shape)[1]
    stripes=(np.floor((x-source.width*.25)/(source.width*.5/4)).astype(int)%2)==0
    palettes=[((233,185,46),(197,43,41)),((242,238,229),(174,32,37)),((16,45,97),(233,185,46)),
        ((33,103,55),(244,233,197)),((71,181,216),(16,45,97))]
    target=HERE/'overlay/Data/Menu/TShirtsIcons';target.mkdir(parents=True,exist_ok=True);records=[]
    for i,(first,second) in enumerate(palettes,1):
        out=pixels.copy();tint=np.where(stripes[:,:,None],np.array(first),np.array(second))*intensity[:,:,None]
        out[:,:,:3][mask]=np.clip(tint[mask],0,255).astype('uint8')
        assert np.array_equal(out[:,:,3],pixels[:,:,3]) and np.array_equal(out[~mask],pixels[~mask])
        path=target/('cx_jagniaki%02d.png'%i);Image.fromarray(out,'RGBA').save(path)
        records.append({'relative':path.relative_to(HERE/'overlay').as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'palette':[first,second]})
    (HERE/'icons-manifest.json').write_text(json.dumps({'source':'Data/Menu/TShirtsIcons/misie01.png','size':source.size,
        'source_alpha_and_unpainted_pixels_unchanged':True,'five_distinct_icons':len(set(r['sha256'] for r in records))==5,'files':records},indent=2)+'\n')


def canonicalize_slot_normals(data,slot):
    """Retain accepted authored normals for fixed profiles across numeric builds."""
    record=json.loads((MODULE/'canonical-normal-components.json').read_text())['slots'][slot]
    assert record['slot']==slot
    nodes=parse(data);out=bytearray(data)
    for component in record['components']:
        offset=component['offset']
        assert offset%4==0 and any(n['pointers'][9]<=offset<n['pointers'][9]+n['nv']*12 for n in nodes if n['type']==2)
        packed=bytes.fromhex(component['packed_float32_hex']);assert len(packed)==4
        out[offset:offset+4]=packed
    result=bytes(out)
    assert hashlib.sha256(result).hexdigest()==record['expected_raw_sha256'], 'Unsupported numeric build or modified profile; review the new baseline instead of silently publishing different models'
    return result,len(record['components'])


def main():
    global HERE,GAME,GENERATED
    parser=argparse.ArgumentParser();parser.add_argument('--game',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path,help='Existing isolated first-lamb work directory')
    parser.add_argument('--artwork-dir',required=True,type=Path,help='kit-02.png..kit-05.png and crest.png')
    args=parser.parse_args();GAME=args.game.resolve(strict=True);HERE=args.output.resolve(strict=True);GENERATED=args.artwork_dir.resolve(strict=True)
    assert not HERE.is_relative_to(GAME), 'Never generate inside the source game'
    assert not (HERE/'assets-manifest.json').exists(), 'Squad output already exists'
    meshes=HERE/'overlay/Data/Meshes/Animals';source=HERE/'reviewed-lamb-base.3da'
    if not source.exists():shutil.copyfile(meshes/'cx_jagniaki_0.3da',source)
    base=source.read_bytes();assert hashlib.sha256(base).hexdigest()=='878dacc8826a852137cac38174593a8103ec9dbefe4c6a7dda89e14760c77914','Only approved first lamb may seed the squad'
    results=[]
    for slot,(head,torso) in enumerate(PROFILES):
        factors={n['name']:head if n['name']=='Bip01 Head' else (1,torso,torso) for n in parse(base) if n['name'] in ('Bip01 Head','Bip01 Pelvis','Bip01 Spine','Bip01 Spine1')}
        data,proof=(base,{'animation_tracks_identical':True,'bone_ids_weights_identical':True,'approved_base_unchanged':True}) if slot==0 else morph_skin(base,factors)
        data,canonical_count=canonicalize_slot_normals(data,slot)
        # Eyes are the FINAL geometry step, after every slot's body/head morph.
        raw_sha256=hashlib.sha256(data).hexdigest();data,eye_proof=fix_eyes(data)
        proof.update({'canonical_authored_normal_components':canonical_count,'raw_before_eye_sha256':raw_sha256,'eye_delta':eye_proof})
        (meshes/('cx_jagniaki_'+str(slot)+'.3da')).write_bytes(data)
        shutil.copyfile(GAME/'Data/Meshes/Animals/mis.ini',meshes/('cx_jagniaki_'+str(slot)+'.ini'))
        results.append({'slot':slot,'sha256':hashlib.sha256(data).hexdigest(),'factors':factors,**proof})
    assert len(set(r['sha256'] for r in results))==7
    textures=HERE/'overlay/Data/Textures/Tshirts';native_eye=Image.open(GAME/'Data/Textures/Tshirts/mis_01.png').convert('RGBA');box=(414,0,508,80)
    for number,filename in KITS.items():
        source=HERE/('texture-source-kit-'+number+'.png');shutil.copyfile(GENERATED/filename,source)
        image=Image.open(source).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
        image.paste(native_eye.crop(box),box[:2]);image.save(textures/('cx_jagniaki_'+number+'.png'))
    texture_results=[];template=(GAME/'Data/Textures/Tshirts/mis_01.tex').read_bytes()
    for number in range(1,6):
        path=textures/('cx_jagniaki_%02d.png'%number);image=Image.open(path)
        assert image.size==(512,512) and image.convert('RGBA').crop(box).tobytes()==native_eye.crop(box).tobytes()
        encoded=encode_tex(image.convert('RGB'),template);target=path.with_suffix('.tex');target.write_bytes(encoded)
        width,height,mips=parse_tex(encoded);assert (width,height,len(mips))==(512,512,10)
        assert target.stat().st_mtime_ns>=path.stat().st_mtime_ns
        texture_results.append({'relative':target.relative_to(HERE/'overlay').as_posix(),'bytes':len(encoded),'mips':len(mips),'sha256':hashlib.sha256(encoded).hexdigest()})
    crest=HERE/'overlay/Data/Menu/logos/cx_jagniellonia.png';crest.parent.mkdir(parents=True,exist_ok=True)
    Image.open(GENERATED/'crest.png').convert('RGBA').resize((256,256),Image.Resampling.LANCZOS).save(crest)
    build_icons()
    report={'format':'PET-SOCCER-JAGNIELLONIA-ASSETS-1','squad':results,'textures':texture_results,
        'same_original_mis_rig_and_ini':True,'approved_single_lamb_sha256':'878dacc8826a852137cac38174593a8103ec9dbefe4c6a7dda89e14760c77914',
        'logo_resolution':[256,256],'logo_alpha_preserved':True,'eye_delta_applied_last':True,'native_game_verified':False}
    (HERE/'assets-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'models':len(results),'kit_caches':len(texture_results),'cache_total_bytes':sum(t['bytes'] for t in texture_results)}))


if __name__=='__main__':main()
