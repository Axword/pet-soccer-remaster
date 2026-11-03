"""Generate deterministic stock-identity variations into an isolated overlay."""
from pathlib import Path
import argparse,hashlib,json,shutil
from native_variants import morph_skin,parse

HERE=Path(__file__).resolve().parent
SOURCE=None
ANIMALS=['mis','Byk','kurczak','dino','zaba','Zyrafa','goryl','lew','pantera','rekin','zolw','robocik']
PROFILES=[((1.05,1.08,.95),1.05),((.96,.92,1.09),.96),((1.09,1.01,1.05),1.00),
          ((.94,1.10,.92),1.045),((1.04,.95,1.08),.975),((.92,1.04,.95),1.02),((1.02,.97,1.02),.95)]

def source_file(stem,suffix):
    return next(p for p in SOURCE.iterdir() if p.name.lower()==(stem+suffix).lower())

def build(ids):
    target=HERE/'overlay/Data/Meshes/Animals';target.mkdir(parents=True,exist_ok=True)
    backup=HERE/'backup-original';backup.mkdir(exist_ok=True)
    report=[]
    for animal in ids:
        stem=ANIMALS[animal];original=source_file(stem,'.3da');data=original.read_bytes()
        ini=source_file(stem,'.ini');shutil.copy2(original,backup/original.name);shutil.copy2(ini,backup/ini.name)
        nodes=parse(data)
        for slot in range(7):
            profile=(slot+animal*3)%7;head,torso=PROFILES[profile]
            factors={n['name']:head if 'head' in n['name'].lower() else (1,torso,torso)
                for n in nodes if n['name'].lower() in ['bip01 head','bip01 pelvis','bip01 spine','bip01 spine1']}
            result,proof=morph_skin(data,factors)
            name='cx_ai_%02d_%d'%(animal,slot)
            (target/(name+'.3da')).write_bytes(result);shutil.copy2(ini,target/(name+'.ini'))
            report.append(dict(animal=animal,slot=slot,profile=profile,source=str(original),
                source_sha256=hashlib.sha256(data).hexdigest(),mesh='Data/Meshes/Animals/'+name+'.3da',
                ini_sha256=hashlib.sha256(ini.read_bytes()).hexdigest(),factors=factors,**proof))
    path=HERE/('chicken-manifest.json' if ids==[2] else 'manifest.json')
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'variants':len(report),'bytes':sum(r['bytes'] for r in report),'manifest':str(path)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true')
    parser.add_argument('--game',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();SOURCE=args.game.resolve(strict=True)/'Data/Meshes/Animals';HERE=args.output.resolve()
    assert not HERE.exists(), 'Choose a fresh output directory'
    assert not HERE.is_relative_to(args.game.resolve()), 'Never generate inside the source game'
    HERE.mkdir(parents=True)
    build(list(range(12)) if args.all else [2])
