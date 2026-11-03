"""Guard one reviewed UpdateSpecialBall method; never overwrites its input."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zipfile
sys.dont_write_bytecode=True


sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile,op

def sha(data):return hashlib.sha256(data).hexdigest()
def body(c):
    raw=c.code('UpdateSpecialBall','()V')[1]
    return raw[8:8+struct.unpack_from('>I',raw,4)[0]]

EXPECTED_BODY = '0584e2f9474b2d1eae97562656525aa45b2fe474d0345e557c5a9c85182d3d89'

def apply(data,helper):
    c=ClassFile(data);before=body(c)
    assert sha(before)==EXPECTED_BODY,'Unreviewed or already patched UpdateSpecialBall'
    h=ClassFile(helper)
    assert h.ref(struct.unpack_from('>H',h.bodyhead,2)[0])=='CXSpecialBall'
    assert struct.unpack_from('>H',helper,6)[0]==47,'Helper must target Java 1.3'
    call=op(184,c.member('CXSpecialBall','BeforeUpdate','(LAIMatch;)Z',10))
    # Eight-byte prefix preserves the alignment of the original tableswitch.
    prefix=b'\x2a'+call+b'\x9a\x00\x04\xb1'
    assert len(prefix)==8
    c.edit('UpdateSpecialBall',lambda _:prefix+before,'()V')
    assert body(c)[8:]==before
    return c.emit(),{'before_body_sha256':sha(before),'after_body_sha256':sha(body(c)),'prefix_bytes':8}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--code-index',type=Path,required=True)
    p.add_argument('--helper',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists(),'Output must be new'
    with zipfile.ZipFile(a.input) as z:
        infos=z.infolist();entries={i.filename:z.read(i) for i in infos}
    assert 'CXSpecialBall.class' not in entries
    helper=a.helper.read_bytes();patched,report=apply(entries['AIMatch.class'],helper)
    index=a.code_index.read_bytes();assert b'CXSpecialBall.class' not in index.splitlines()
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.output/'code.pak','w') as z:
        for i in infos:z.writestr(i,patched if i.filename=='AIMatch.class' else entries[i.filename])
        i=zipfile.ZipInfo('CXSpecialBall.class',(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(i,helper)
    (a.output/'code_inf.pak').write_bytes(index.rstrip(b'\r\n')+b'\r\nCXSpecialBall.class\r\n')
    with zipfile.ZipFile(a.output/'code.pak') as z:
        assert all(z.read(n)==v for n,v in entries.items() if n!='AIMatch.class')
    report.update(input_sha256=sha(a.input.read_bytes()),output_sha256=sha((a.output/'code.pak').read_bytes()),helper_sha256=sha(helper),changed_classes=['AIMatch.class','CXSpecialBall.class'],native_test_required=True)
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
