"""Subtle native fur patterns. Protected BC1 blocks stay byte-for-byte original."""
from pathlib import Path
import argparse,hashlib,json,sys
from functools import lru_cache
import numpy as np
from PIL import Image,ImageFilter
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'base-maps'))
from native_tex import parse_tex,decode_bc1,assemble_tex,decode_level
from build_variants import ANIMALS

SOURCE=None
TARGET=HERE/'overlay/Data/Textures/Tshirts'

@lru_cache(maxsize=1)
def source_files():return {p.name.lower():p for p in SOURCE.iterdir() if p.is_file()}
def find(name):return source_files()[name.lower()]

def stable_fur_mask(stem):
    paths=[find(stem+'_'+prefix+str(i).zfill(2)+'.png') for prefix in ('','B') for i in range(1,6)]
    images=np.array([np.asarray(Image.open(p).convert('RGBA')) for p in paths],dtype=np.int16)
    color=images[0,:,:,:3]
    cloth=(images[:,:,:,:3].max(0)-images[:,:,:,:3].min(0)).max(2)>3
    # Original kit, eyes/pupils, highlights and transparent/outside pixels are
    # protected, then expanded conservatively beyond their texture boundaries.
    protected=cloth|(color.max(2)<24)|(color.min(2)>236)|(images[:,:,:,3].min(0)<250)
    expanded=np.asarray(Image.fromarray(protected.astype('uint8')*255).filter(ImageFilter.MaxFilter(5)))>0
    return ~expanded

def shade_bc1(chunk,pattern,eligible):
    """Change only original RGB565 endpoints; retain every original selector.

    No fresh lossy fit is run, so fur detail/palette structure and all protected
    blocks remain exactly authored. Preserve each block's three/four-color mode.
    """
    old=np.frombuffer(chunk,dtype='<u2').reshape(-1,4);new=old.copy()
    endpoint=old[:,:2].astype(np.uint32)
    r=(endpoint>>11)&31;g=(endpoint>>5)&63;b=endpoint&31
    colors=np.stack(((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2)),axis=2).astype(float)
    values=np.clip(np.rint(colors*(1+pattern[:,None,None])*np.array([31,63,31])/255),0,[31,63,31]).astype(np.uint16)
    packed=(values[:,:,0]<<11)|(values[:,:,1]<<5)|values[:,:,2]
    valid=(endpoint[:,0]>endpoint[:,1])==(packed[:,0]>packed[:,1])
    change=eligible&valid;new[change,:2]=packed[change]
    assert np.array_equal(new[:,2:],old[:,2:])
    assert np.array_equal(new[~eligible],old[~eligible])
    return new.tobytes(),int(np.any(new!=old,axis=1).sum())

def build(animal_ids):
    TARGET.mkdir(parents=True,exist_ok=True);records=[]
    for animal in animal_ids:
        stem=ANIMALS[animal].lower();mask=stable_fur_mask(stem);height,width=mask.shape
        yy,xx=np.mgrid[:height,:width];xx=xx/width;yy=yy/height
        for prefix in ('','b'):
            for color in range(1,6):
                template_path=find(stem+'_'+prefix+str(color).zfill(2)+'.tex');template=template_path.read_bytes()
                w,h,chunks=parse_tex(template);assert (w,h)==(width,height)
                images=[decode_bc1(chunk,(max(1,w>>level),max(1,h>>level))) for level,chunk in enumerate(chunks)]
                for slot in range(7):
                    profile=(slot+animal*3)%7
                    pattern=np.sin((xx*(3+profile%3)+yy*(2+profile%2)+profile*.31)*np.pi*2)
                    pattern=.65*pattern+.35*np.sin((xx*7-yy*5+profile*.17)*np.pi*2)
                    # All seven profiles are distinct, with at most 3% local
                    # value change in existing fur/pelt/metal texture shading.
                    pattern=np.clip(pattern*.021+(profile-3)*.0025,-.03,.03)
                    generated=[];changed_blocks=0;eligible_blocks=0
                    for level,(chunk,image) in enumerate(zip(chunks,images)):
                        mw,mh=image.size;factor=1<<level
                        if min(mw,mh)<4:generated.append(chunk);continue
                        smallmask=mask.reshape(mh,factor,mw,factor).all(axis=(1,3))
                        blocks=smallmask.reshape(mh//4,4,mw//4,4).all(axis=(1,3)).ravel()
                        eligible_blocks+=int(blocks.sum())
                        if not blocks.any():generated.append(chunk);continue
                        smallpattern=pattern.reshape(mh,factor,mw,factor).mean(axis=(1,3))
                        blockpattern=smallpattern.reshape(mh//4,4,mw//4,4).mean(axis=(1,3)).ravel()
                        encoded,changed=shade_bc1(chunk,blockpattern,blocks)
                        changed_blocks+=changed;generated.append(encoded)
                    result=assemble_tex(template,generated);assert changed_blocks>0
                    name=stem+'_'+prefix+str(color).zfill(2)+'_cx'+str(slot)
                    tex=TARGET/(name+'.tex')
                    # A valid fallback/readback PNG mirrors the actual native
                    # texture; the engine's prepared TEX remains the fast path.
                    decoded=decode_level(result);pixels=np.asarray(decoded);old_pixels=np.asarray(images[0])
                    difference=np.abs(pixels.astype(np.int16)-old_pixels.astype(np.int16))
                    assert np.array_equal(pixels[~mask],old_pixels[~mask])
                    assert difference.max()<=9
                    png=TARGET/(name+'.png');decoded.save(png,optimize=True)
                    tex.write_bytes(result) # Keep prepared cache newer than fallback PNG.
                    records.append({'animal':animal,'slot':slot,'source':str(template_path),
                        'source_sha256':hashlib.sha256(template).hexdigest(),'texture':'Data/Textures/Tshirts/'+name+'.png',
                        'tex_sha256':hashlib.sha256(result).hexdigest(),'size':[w,h],'mips':len(chunks),
                        'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
                        'bytes':len(result),'changed_blocks':changed_blocks,'eligible_blocks':eligible_blocks,
                        'protected_blocks_exact':True,'max_authored_value_change':.03,
                        'max_native_channel_delta':int(difference.max()),'mean_native_channel_delta':float(difference.mean())})
        print('TEXTURES',animal,stem,len(records),flush=True)
    (HERE/('chicken-textures.json' if animal_ids==[2] else 'texture-manifest.json')).write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'textures':len(records),'tex_bytes':sum(r['bytes'] for r in records)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true')
    parser.add_argument('--game',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();SOURCE=args.game.resolve(strict=True)/'Data/Textures/Tshirts';HERE=args.output.resolve()
    assert not HERE.is_relative_to(args.game.resolve()), 'Never generate inside the source game'
    TARGET=HERE/'overlay/Data/Textures/Tshirts'
    assert not TARGET.exists(), 'Texture output already exists'
    HERE.mkdir(parents=True,exist_ok=True)
    build(list(range(12)) if args.all else [2])
