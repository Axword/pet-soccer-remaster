"""Isolated tournament fix: complete UI hiding and draw pairs once at Begin."""
from pathlib import Path
import argparse, hashlib, json, struct, sys, zipfile

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
sys.path.insert(0,str(ROOT))
from tools.classfile import ClassFile

HIDE_SHA='d1aa2c8322ad8d51669d5bb2bc9afedc9001e5e64a6e505d6ad442da32dd2d02'
CX_SHA='da81aec9cab4e817ea6f3ef016eceeaf0fe66a1eda36614e43962022d3513e1b'
SETUP_SHA='a7320e3b6a93b721fecd846a4b8afa25a20d223d6c851cb7bc463ff578449922'
def sha(data):return hashlib.sha256(data).hexdigest()
def code(c,name,desc):
    raw=c.code(name,desc)[1];n=struct.unpack_from('>I',raw,4)[0]
    return raw[8:8+n]

def apply(classes,compiled_dir):
    c=ClassFile(classes['SoccerMainMenuModule.class'])
    before=code(c,'HideAllUIs','()V')
    assert sha(before)==HIDE_SHA, 'HideAllUIs changed; inspect instead of regenerating'
    assert before[23:29]==b'\x1b\x10\x12\xa1\xff\xe8'
    assert code(c,'<init>','()V')[20:22]==b'\x10\x14', 'Expected twenty registered UIs'
    after=before[:25]+b'\x14'+before[26:]
    attr=c.code('HideAllUIs','()V');raw=attr[1]
    attr[1]=raw[:8]+after+raw[8+len(before):]
    module=c.emit()
    assert sum(a!=b for a,b in zip(module,classes['SoccerMainMenuModule.class']))==1
    assert len(module)==len(classes['SoccerMainMenuModule.class'])
    assert sha(classes['CXKnockout.class'])==CX_SHA, 'Controller changed; inspect current source'
    assert sha(classes['CXKnockoutSetup.class'])==SETUP_SHA, 'Setup changed; inspect current source'
    controller=(Path(compiled_dir)/'CXKnockout.class').read_bytes()
    setup=(Path(compiled_dir)/'CXKnockoutSetup.class').read_bytes()
    assert struct.unpack_from('>H',controller,6)[0]==47
    assert struct.unpack_from('>H',setup,6)[0]==47
    updates={'SoccerMainMenuModule.class':module,'CXKnockout.class':controller,
             'CXKnockoutSetup.class':setup}
    return updates,{'hide_bound':{'before':18,'after':20,'changed_class_bytes':1},
                    'draw':'Fisher-Yates once at successful Begin; setup vector unchanged',
                    'labels':'full club name unless distinct player label; Fit measures available width',
                    'preview':'Custom setup Hide deactivates its 3D preview',
                    'legacy_six_team_league_classes_unchanged':True}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compiled',type=Path,default=ROOT/'build/java')
    args=parser.parse_args()
    if args.output.exists() or args.input.resolve()==args.output.resolve():
        parser.error('Use a new output archive outside the input file')
    with zipfile.ZipFile(args.input) as z:
        infos=z.infolist();before={i.filename:z.read(i.filename) for i in infos}
    updates,receipt=apply(before,args.compiled)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(args.output,'w') as z:
        for i in infos:z.writestr(i,updates.get(i.filename,before[i.filename]))
    receipt.update(input_sha256=sha(args.input.read_bytes()),output_sha256=sha(args.output.read_bytes()),
                   changed_classes=sorted(updates),runtime_visual_verification_required=True)
    args.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps(receipt))
if __name__=='__main__':main()
