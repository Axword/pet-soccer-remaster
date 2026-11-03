"""Guarded owned Online 1v1 hooks; does not export any stock class source.

Integrator imports apply_match({class_entry: bytes}) after UI hooks. The changed
stock methods are fingerprinted against the current GMWL archive at author time.
"""
from pathlib import Path
import hashlib, json, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.classfile import ClassFile,op,append,U2,U4

def apply_match(before):
    expected=json.loads((R/'method-fingerprints.json').read_text())
    updates={};changes=[]
    def edit(class_name,name,desc,fn):
        entry=class_name+'.class'
        c=ClassFile(updates.get(entry,before[entry]))
        raw=c.code(name,desc)[1]
        key=class_name+'.'+name+desc
        digest=hashlib.sha256(raw).hexdigest()
        assert digest==expected[key],(key,'input method differs',digest)
        c.edit(name,lambda body:fn(c,body),desc)
        updates[entry]=c.emit();changes.append(key)
    def call(c,method,desc):return op(184,c.member('CXOnlineMatch',method,desc,10))
    def guard(c,method='shouldSkipSimulation'):
        # Eight-byte aligned entry guard: branch lands at first stock instruction.
        return call(c,method,'()Z')+b'\x99\0\x05\xb1\0'
    def frame(c,body):
        prefix=b'\x2a'+call(c,'beforeFrame','(LSoccerModule;)Z')+b'\x99\0\x08\xb1'+b'\0'*4
        assert len(prefix)==12
        suffix=b'\x2a'+call(c,'afterFrame','(LSoccerModule;)V')
        return prefix+append(body,suffix)
    edit('SoccerModule','OnFrame','()V',frame)
    # A full-time clock alone is insufficient (goal/out/corner breaks can hold
    # it there). Observe the actual engine terminal transition after its body.
    edit('SoccerModule','OnMatchEnd','()V',lambda c,b:append(b,b'\x2a'+call(c,'onMatchEnd','(LSoccerModule;)V')))
    def arg_guard(c,body,method,desc,loads):
        p=loads+call(c,method,desc)
        target=(len(p)+4+3)&~3
        p+=b'\x99'+(target-len(p)).to_bytes(2,'big')+b'\xb1'
        p+=b'\0'*(target-len(p))
        assert len(p)%4==0
        return p+body
    edit('SoccerModule','OnInputKey','(IZC)V',lambda c,b:arg_guard(c,b,'moduleKey','(LSoccerModule;IZC)Z',b'\x2a\x1b\x1c\x1d'))
    edit('InputDigital','Translate','(IIZ)V',lambda c,b:arg_guard(c,b,'digital','(LInputDigital;IIZ)Z',b'\x2a\x1b\x1c\x1d'))
    edit('InputAnalog','Translate','(IIF)V',lambda c,b:arg_guard(c,b,'analog','(LInputAnalog;IIF)Z',b'\x2a\x1b\x1c\x25'))
    # Block guest AI/gameplay callbacks and native collision consequences. Stock
    # physics itself is disabled per actor, while native animation keeps running.
    for cls,method,desc in [
        ('AIMatch','Update','()V'),('AIFootBaller','OnFrame','()V'),
        ('AIFootBaller','Update','()V'),('AIFootBaller','OnPhysicsUpdate','(FF)V'),
        ('AIFootBaller','OnCollisionFullInfoMove','(LControlObject;LVector;LVector;LVector;)V'),
        ('Ball','OnFrame','()V'),('Ball','OnPhysicsUpdate','(FF)V'),
        ('Ball','OnCollisionFullInfo','(LControlObject;LVector;LVector;)V')]:
        edit(cls,method,desc,lambda c,b:guard(c)+b)
    edit('FootBaller','PlayAnim','(Ljava/lang/String;I)I',lambda c,b:b'\x2a\x2b\x1c'+call(c,'animation','(LFootBaller;Ljava/lang/String;I)V')+b'\0\0'+b)
    edit('PetSoccerHud','ShowEventInfo','(I)V',lambda c,b:b'\x1b'+call(c,'hudEvent','(I)V')+b)
    # The stock end-commentary assumes a local league/MatchData lifecycle.
    # Online omits this one announcement; offline executes the exact old body.
    edit('Commentator','CommentMatchEnd','()V',lambda c,b:guard(c,'isActive')+b)
    edit('SoccerGame','OnFrame','()V',lambda c,b:append(b,call(c,'globalTick','()V')))
    edit('SoccerGame','EndModule','()V',lambda c,b:call(c,'beforeReturnToMenu','()V')+b'\0'*5+append(b,call(c,'returnedToMenu','()V')))
    # ExitToMenu has two returns. Wrap its Java body so every successful exit is
    # observed after deactivation; branch offsets inside the stock body stay exact.
    entry='SoccerGame.class';c=ClassFile(updates[entry]);name='ExitToMenu';desc='()V'
    assert hashlib.sha256(c.code(name,desc)[1]).hexdigest()==expected['SoccerGame.'+name+desc]
    original=next(m for m in c.methods if c.ref(m[1])==name and c.ref(m[2])==desc)
    renamed='CXOnlineOriginalExitToMenu'
    assert not any(c.ref(m[1])==renamed for m in c.methods)
    original[1]=c.add(1,renamed)
    wrapper=guard(c,'deferReturnToMenu')+call(c,'beforeReturnToMenu','()V')+b'\x2a'+op(183,c.member('SoccerGame',renamed,desc,10))+call(c,'returnedToMenu','()V')+b'\xb1'
    c.methods.append([1,c.add(1,name),c.add(1,desc),[[c.add(1,'Code'),U2(1)+U2(1)+U4(len(wrapper))+wrapper+b'\0\0\0\0']]])
    updates[entry]=c.emit();changes.append('SoccerGame.ExitToMenu()V')
    # An Online session never writes the temporary player/options to disk.
    edit('SoccerGame','SaveAttrib','()V',lambda c,b:guard(c,'isActive')+b)
    return updates,changes
