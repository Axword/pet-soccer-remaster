"""Enlarge existing Minecraft atlases with exact nearest-neighbour pixels."""
from pathlib import Path
import argparse, hashlib, json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True,help='Texture directory, read only')
    p.add_argument('--output',type=Path,required=True,help='New output directory')
    p.add_argument('--width',type=int,default=2048)
    a=p.parse_args()
    from PIL import Image
    source=a.input.resolve();output=a.output.resolve()
    if source==output or output.is_relative_to(source):p.error('Use a separate output directory')
    rows=[]
    for file in sorted(source.glob('cx_mc_*.png')):
        target=output/file.name
        if target.exists():p.error('Output already exists: '+str(target))
        with Image.open(file) as image:
            image=image.convert('RGBA')
            ratio=a.width//image.width
            if ratio<1 or ratio&(ratio-1) or ratio*image.width!=a.width:p.error('Width must be a power-of-two integer enlargement')
            enlarged=image.resize((image.width*ratio,image.height*ratio),Image.Resampling.NEAREST)
            assert enlarged.resize(image.size,Image.Resampling.NEAREST).tobytes()==image.tobytes()
            output.mkdir(parents=True,exist_ok=True);enlarged.save(target)
            rows.append({'file':file.name,'source_size':image.size,'output_size':enlarged.size,
                         'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'exact_pixel_roundtrip':True})
    if not rows:p.error('No cx_mc_*.png atlases found')
    (output/'upscale-report.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    print('Wrote',len(rows),'pixel-preserving atlases')

if __name__=='__main__':main()
