"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

LAST_REPORT=[]

def instructions(body):
    """Decode boundaries; never replace a matching byte sequence in an operand."""
    i=0
    two={16,18,21,22,23,24,25,54,55,56,57,58,169,188}
    three={17,19,20,132,*range(153,169),178,179,180,181,182,183,184,187,189,192,193,198,199}
    while i<len(body):
        start=i;code=body[i];i+=1
        if code in two:i+=1
        elif code in three:i+=2
        elif code in (185,186,200,201):i+=4
        elif code==197:i+=3
        elif code==196:
            sub=body[i];i+=5 if sub==132 else 3
        elif code==170:
            i=(i+3)&~3
            _,lo,hi=struct.unpack_from('>iii',body,i)
            i+=12+(hi-lo+1)*4
        elif code==171:
            i=(i+3)&~3
            _,count=struct.unpack_from('>ii',body,i)
            i+=8+count*8
        assert i<=len(body),(start,code,i,len(body))
        yield start,code
    assert i==len(body)

def wrapper(template):
    c=C(template)
    c.bodyhead=U2(0x31)+U2(c.clazz('CXLog'))+U2(c.clazz('java/lang/Object'))
    c.interfaces=U2(0);c.fields=[];c.methods=[];c.attrs=[]
    # Exception range covers only the original native console invocation.
    # Unrelated exceptions continue to propagate; fallback writes a raw log.
    body=b'\x2a'+op(184,c.member('GameObject','LogLine','(Ljava/lang/String;)V',10))+b'\xb1\x57\x2a'+op(184,c.member('GameObject','CrashLog','(Ljava/lang/String;)V',10))+b'\xb1'
    handler=U2(0)+U2(4)+U2(5)+U2(c.clazz('java/lang/IndexOutOfBoundsException'))
    attribute=U2(1)+U2(1)+U4(len(body))+body+U2(1)+handler+U2(0)
    c.methods.append([9,c.add(1,'SafeLog'),c.add(1,'(Ljava/lang/String;)V'),[[c.add(1,'Code'),attribute]]])
    return c.emit()

def apply(classes,scope='all'):
    assert scope in ('all','gameplay')
    global LAST_REPORT
    LAST_REPORT=[];updates={}
    core={'Match','Team','FootBaller','Ball','TeamController','Individual','Strategy','SoccerModule','Clock','GameField','SelectionDest'}
    for filename,data in classes.items():
        if not filename.endswith('.class') or filename=='CXLog.class':continue
        stem=filename[:-6]
        if scope=='gameplay' and stem not in core and not stem.startswith('AI'):continue
        c=C(data)
        refs={i for i,x in enumerate(c.cp) if x and x[0]==10 and c.ref(i)=='GameObject.LogLine.(Ljava/lang/String;)V'}
        if not refs:continue
        safe=c.member('CXLog','SafeLog','(Ljava/lang/String;)V',10)
        methods=[]
        for method in c.methods:
            for attribute in method[3]:
                if c.ref(attribute[0])!='Code':continue
                raw=attribute[1];length=struct.unpack_from('>I',raw,4)[0]
                body=bytearray(raw[8:8+length]);sites=[]
                for offset,opcode in instructions(body):
                    if opcode==184 and struct.unpack_from('>H',body,offset+1)[0] in refs:
                        struct.pack_into('>H',body,offset+1,safe);sites.append(offset)
                if sites:
                    attribute[1]=raw[:8]+body+raw[8+length:]
                    methods.append({'name':c.ref(method[1]),'descriptor':c.ref(method[2]),'sites':sites})
        if methods:
            updates[filename]=c.emit()
            LAST_REPORT.append({'class':filename,'calls':sum(len(m['sites']) for m in methods),'methods':methods})
    expected=wrapper(classes['InputAction.class'])
    if classes.get('CXLog.class')!=expected:updates['CXLog.class']=expected
    return updates
