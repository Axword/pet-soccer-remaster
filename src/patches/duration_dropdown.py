"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

MARKER=b'ControlObject("UIComboBox","ID_COMBOBOX_TIME","Specific")'

CHILDREN=[b'ControlObject("UIListBox","ID_COMBO_LIST","Specific")',
          b'Menu("UIMenu","ID_LIST","Specific")',
          b'MenuButton("UIMenuButton","ID_BUTTON","","Standard","Specific")']

def span(data,marker):
    assert data.count(marker)==1,(marker,'ambiguous or missing widget')
    start=data.index(marker);opening=data.index(b'{',start);depth=0
    for pos in range(opening,len(data)):
        if data[pos:pos+1]==b'{':depth+=1
        elif data[pos:pos+1]==b'}':
            depth-=1
            if not depth:return start,pos+1
    raise AssertionError('Unterminated time combo')

def apply(data):
    start,end=span(data,MARKER);time=data[start:end]
    assert re.search(rb'LogicSize\(0\.335,0\.053333335\)',time)
    for marker in CHILDREN:
        lo,hi=span(time,marker);child=time[lo:hi]
        first=re.search(rb'LogicSize\(([^,]+),([^\)]+)\)',child)
        assert first and first[1] in [b'0.15',b'0.335'] and first[2]==b'0.053333335',(marker,'unexpected bounds')
        a,b=lo+first.start(1),lo+first.end(1)
        time=time[:a]+b'0.335'+time[b:]
    return data[:start]+time+data[end:]
