"""Generate six tournament SCR layouts from a read-only original Pet Soccer.

Use --game for the original game and --output for a new directory outside it.
No game/source/package is changed. Original UI declarations and setup composition
are read locally; no original game asset is embedded in this generator.
The Java entry IDs are intentionally identical to the existing controller.
"""
from pathlib import Path
import argparse,hashlib,json,re

ATLAS='data/menu/p_menu.png'
QY=[0.29,0.35,0.43,0.49,0.57,0.63,0.71,0.77]
SY=[(QY[i]+QY[i+1])/2 for i in range(0,8,2)]
FY=[(SY[i]+SY[i+1])/2 for i in range(0,4,2)]
X=[0.055,0.365,0.675]
ROW_W=0.27
ROW_H=0.05

def number(value):
    if isinstance(value,int):return str(value)
    text=f'{value:.9f}'.rstrip('0').rstrip('.')
    return text if '.' in text else text+'.0'

def call(name,*args):
    encoded=','.join('"'+s+'"' if isinstance(s,str) else number(s) for s in args)
    return name+'('+encoded+')'

def block(tag,cls,ident,props,children=()):
    decl=call(tag,cls,ident,'Specific')
    return decl+'\n{\n'+''.join('   '+p+'\n' for p in props)+''.join(
        '\n'+'\n'.join('   '+line for line in child.splitlines())+'\n' for child in children)+'}\n'

def style(font,x,y,w,h,*,relative=False,visible=1,mouse=0,text='',flags=18):
    return [call('Text',text),call('TextColor',1.0,1.0,1.0),call('Font',font),
        call('TextPosFlags',flags),call('LogicSize',w,h),call('LogicPos',x,y),
        call('Mouse',mouse),call('Keyboard',0),call('Joy',0),call('Visible',visible),
        call('CursorVisible',1),call('ParentPositioning',1),call('ParentCenteringX',0),
        call('ParentCenteringY',0),call('ParentSizingX',int(relative)),call('ParentSizingY',int(relative))]

def solid():
    # Actual opaque original Championships2 border pixel, RGBA198,208,197,255.
    # Uses the existing atlas, no new drawing/texture or colour substitution.
    return call('TextureRect',ATLAS,1024.0,1024.0,945.0,59.0,946.0,60.0)

def build(width,height,body,jazz,corners,declarations):
    nodes=[];audit=[]
    def add(node,kind,ident,rect):
        nodes.append(node);audit.append(dict(kind=kind,id=ident,rect=rect))
    frame=style(body,0.015,0.17,0.97,0.72)
    frame += [call('FrameCornerSize',*corners),call('TextureRect',ATLAS,1024.0,1024.0,262.0,601.0,585.0,921.0)]
    add(block('Static','UIStatic','ID_CX_BRACKET_FRAME',frame),'frame','ID_CX_BRACKET_FRAME',[0.015,0.17,0.97,0.72])
    for i,title in enumerate(('CWIERCFINALY','POLFINALY','FINAL')):
        ident='ID_CX_ROUND_'+str(i+1)
        add(block('Static','UIStatic',ident,style(body,X[i],0.215,ROW_W,0.045,text=title,flags=34)),
            'heading',ident,[X[i],0.215,ROW_W,0.045])

    serial=[0]
    def line(x1,y1,x2,y2):
        serial[0]+=1;ident='ID_CX_JOIN_'+str(serial[0])
        # Two physical pixels at each original reference resolution.
        thick_x=2.0/width;thick_y=2.0/height
        if abs(y2-y1)<1e-8:
            rect=[min(x1,x2),y1-thick_y/2,abs(x2-x1)+thick_x,thick_y]
        else:
            rect=[x1-thick_x/2,min(y1,y2),thick_x,abs(y2-y1)+thick_y]
        add(block('Window','UIWindow',ident,style(body,*rect)+[solid()]),'line',ident,rect)

    # Each pair joins at its midpoint before reaching the next-round slot.
    for column,ys in ((0,QY),(1,SY)):
        right=X[column]+ROW_W;next_left=X[column+1];junction=(right+next_left)/2
        for i in range(0,len(ys),2):
            first,last=ys[i:i+2];middle=(first+last)/2
            line(right,first,junction,first)
            line(right,last,junction,last)
            line(junction,first,junction,last)
            line(junction,middle,next_left,middle)
    # Group the two finalists as a single final. The existing winner overlay
    # remains the final winner display; no extra unbound winner node is added.
    final_right=X[2]+ROW_W
    line(final_right,FY[0],0.957,FY[0])
    line(final_right,FY[1],0.957,FY[1])
    line(0.957,FY[0],0.957,FY[1])

    for column,(prefix,ys) in enumerate((('ID_QFINAL_',QY),('ID_SEMIFINAL_',SY),('ID_FINAL_',FY))):
        for n,y in enumerate(ys,1):
            ident=prefix+str(n);rect=[X[column],y-ROW_H/2,ROW_W,ROW_H]
            props=style(body,*rect)
            props += [call('FrameCornerSize',3,3),call('TextureRect',ATLAS,1024.0,1024.0,943.0,59.0,952.0,68.0)]
            logo=block('Window','UIWindowBlinking','ID_LOGO',
                style(body,0.02,0.06,0.125,0.88,relative=True))
            # Name is a sibling of the icon, bounded by the full row. It is no
            # longer a 0.2-wide global label clipped by a tiny icon parent.
            name=block('Static','UIStatic','ID_NAME',
                style(body,0.155,0.05,0.83,0.90,relative=True,text='?',flags=18))
            lost=block('Window','UIWindow','ID_LOST',
                style(body,0.155,0.46,0.83,0.08,relative=True,visible=0)+[solid()])
            add(block('Static','UIStatic',ident,props,(logo,name,lost)),'entry',ident,rect)

    caption='REMIS PO DWOCH POLOWACH: ZLOTY GOL'
    add(block('Static','UIStatic','ID_CX_GOLDEN_RULE',
        style(body,0.06,0.81,0.88,0.04,text=caption,flags=34)),
        'caption','ID_CX_GOLDEN_RULE',[0.06,0.81,0.88,0.04])

    def button(ident,label,x):
        props=[call('Checked',0),call('Disabled',0),call('CanCallPress',0),call('CanCheck',0),
            call('MouseLeaveDestroyFocus',1),call('CheckSound','data/sounds/click'),
            call('TextureCheckedRect',ATLAS,1024.0,1024.0,203.0,946.0,402.0,992.0),
            call('TextureDisabledRect',ATLAS,1024.0,1024.0,1.0,946.0,200.0,992.0),
            call('TextDisableColor',0.5019608,0.5019608,0.5019608),
            call('CallPressPeriod',0.1),call('DoubleClick',0.3),call('Command',1),call('Notify',1),
            call('CanFocus',1),call('SelKeyUp',208),call('SelKeyDown',208),
            call('FocusSound','data/sounds/highlight')]
        props+=style(jazz,x,0.0,0.24875,0.08,text=label,flags=34,mouse=1)
        props=[call('Keyboard',1) if p=='Keyboard(0)' else p for p in props]
        props += [call('TextureRect',ATLAS,1024.0,1024.0,801.0,1.0,1000.0,47.0)]
        # MenuButton has a five-string declaration, unlike the other node types.
        result=block('MenuButton','UIMenuButtonFlying',ident,props)
        return result.replace(call('MenuButton','UIMenuButtonFlying',ident,'Specific'),
            call('MenuButton','UIMenuButtonFlying',ident,label,'Standard','Specific'),1)
    menu=style(body,0.0,0.90166664,1.0,0.083333336,mouse=1)
    menu += [call('Command',1),call('Notify',1),call('CanFocus',0),call('SelKeyUp',208),call('SelKeyDown',208)]
    menu=[call('Keyboard',1) if p=='Keyboard(0)' else p for p in menu]
    nodes.append(block('Menu','UIMenu','ID_MENU',menu,
        (button('ID_BACK','&&MenuBack&&',0.18),button('ID_OK','GRAJ',0.57))))
    audit += [dict(kind='button',id='ID_BACK',rect=[0.18,0.90166664,0.24875,0.08]),
        dict(kind='button',id='ID_OK',rect=[0.57,0.90166664,0.24875,0.08])]

    # Retain the controller's intentional winner overlay; hidden at load.
    winner=block('Static','UIStaticBlinking','ID_INFO_SCREEN_TEXT',
        style(jazz,0.12,0.30,0.76,0.38,relative=True,flags=34))
    nodes.append(block('Static','UIStatic','ID_INFO_SCREEN',
        style(body,0.0,0.0,1.0,1.0,visible=0)+[call('Texture','black.png')],(winner,)))

    root=style(body,0.0,0.0,1.0,1.0,mouse=1)
    root=[call('Keyboard',1) if p=='Keyboard(0)' else p for p in root]
    root=[call('ParentPositioning',0) if p=='ParentPositioning(1)' else p for p in root]
    root += [call('Command',1),call('Notify',1),call('CanFocus',0),call('SelKeyUp',0),
        call('SelKeyDown',15),call('Cursor','data/textures/cursors/cursor.png')]
    text=declarations+'// Three-column eight-team bracket. Existing atlas and original loaded fonts.\n'
    text+=call('Interface','UI_CX_KNOCKOUT')+'\n{\n'+''.join('   '+p+'\n' for p in root)
    text+=''.join('\n'+'\n'.join('   '+line for line in n.splitlines())+'\n' for n in nodes)+'}\n'
    assert text.isascii()
    assert 'MSSansSerif' not in text and 'MS Sans Serif' not in text
    assert not re.search(r'[(,]\s*-?\.\d',text)
    assert text.count('{')==text.count('}')
    ids=[m.group(1) for m in re.finditer(r'(?:Static|Window|Menu|MenuButton)\("[^"]+","([^"]+)"',text)]
    for prefix,count in (('ID_QFINAL_',8),('ID_SEMIFINAL_',4),('ID_FINAL_',2)):
        assert all(ids.count(prefix+str(n))==1 for n in range(1,count+1))
    for ident in ('ID_LOGO','ID_NAME','ID_LOST'):assert ids.count(ident)==14
    fonts=set(re.findall(r'^\s*Font\("([^"]+)"\)',text,re.M))
    assert fonts=={body,jazz}
    for row in audit:
        x,y,w,h=row['rect'];assert x>=0 and y>=0 and x+w<=1.000001 and y+h<=1.000001,row
    entry=[r for r in audit if r['kind']=='entry']
    for a in entry:
        ax,ay,aw,ah=a['rect']
        for b in entry:
            if a is b:continue
            bx,by,bw,bh=b['rect']
            assert not (min(ax+aw,bx+bw)>max(ax,bx)+1e-8 and min(ay+ah,by+bh)>max(ay,by)+1e-8),(a,b)
    return text,audit,fonts

def extract_block(text,kind,ident):
    pattern=r'\b'+re.escape(kind)+r'\([^\n]*"'+re.escape(ident)+r'"[^\n]*\)\s*\{'
    found=re.search(pattern,text)
    if not found:raise ValueError('Missing original control '+ident)
    start=found.start();pos=found.end();depth=1;quoted=False;escaped=False
    while depth:
        char=text[pos];pos+=1
        if char=='"' and not escaped:quoted=not quoted
        if not quoted:
            if char=='{':depth+=1
            elif char=='}':depth-=1
        escaped=char=='\\' and not escaped
    return start,pos,text[start:pos]

def setup_layout(raw):
    text=raw.decode('cp1250')
    if 'ID_CX_TOURNAMENT' in text:
        raise ValueError('Use the original game Multiplayer SCR, before mod buttons were added')
    if text.count('Interface("UI_MULTIPLAYER")')!=1:
        raise ValueError('Unexpected original Multiplayer interface')
    setup=text.replace('Interface("UI_MULTIPLAYER")','Interface("UI_CX_KNOCKOUT_SETUP")')
    start,end,button=extract_block(setup,'MenuButton','ID_OK')
    if '&&MenuOK&&' not in button:raise ValueError('Unexpected original OK button')
    setup=setup[:start]+button.replace('&&MenuOK&&','DALEJ')+setup[end:]
    font=next(f for f in re.findall(r'Font\("([^"]+)"\)',text) if f.startswith('FLRoman'))
    rule='\n Static("UIStatic","ID_CX_GOLD_RULE","Specific")\n {\n Text("Remis po 2 polowach: zloty gol")\n TextColor(1,1,1)\n Font("'+font+'")\n TextPosFlags(34)\n LogicPos(0.05,0.17)\n LogicSize(0.9,0.045)\n ParentPositioning(1)\n ParentCenteringX(0)\n ParentCenteringY(0)\n Mouse(0)\n Keyboard(0)\n Joy(0)\n Visible(1)\n }\n'
    setup=setup[:setup.rfind('}')]+rule+setup[setup.rfind('}'):]
    result=setup.encode('cp1250')
    assert result.count(b'ID_CX_GOLD_RULE')==1
    assert b'Remis po 2 polowach: zloty gol' in result
    assert not re.search(rb'[(,]\s*-?\.\d',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True,help='Read-only original Polish Pet Soccer directory')
    parser.add_argument('--output',type=Path,required=True,help='New output directory outside the original game')
    args=parser.parse_args()
    game=args.game.resolve();output=args.output.resolve()
    if output==game or output.is_relative_to(game):parser.error('Output must be outside the original game')
    if output.exists():parser.error('Use a new output directory')
    source=game/'Data/Menu/scr'
    required=[source/'Championships2.scr']+[source/('Multiplayer'+s+'.scr') for s in ('640','','1024')]
    for path in required:
        if not path.is_file():parser.error('Missing original UI input: '+str(path))
    declarations=(source/'Championships2.scr').read_text(encoding='cp1250').split('//------ UI stuff')[0]
    dest=output/'Data/Menu/scr';receipt=[];payload={}
    for suffix,w,h,body,jazz,corners in (
        ('640',640,480,'FLRoman16','FLJazz26',(15,18)),
        ('',800,600,'FLRoman21','FLJazz32',(20,24)),
        ('1024',1024,768,'FLRoman28','FLJazz42',(25,30))):
        text,layout,fonts=build(w,h,body,jazz,corners,declarations)
        name='CXKnockout'+suffix+'.scr'
        raw=text.replace('\n','\r\n').encode('ascii');payload[name]=raw
        receipt.append(dict(path='Data/Menu/scr/'+name,sha256=hashlib.sha256(raw).hexdigest(),reference_size=[w,h],
            bytes=len(raw),fonts=sorted(fonts),entry_count=14,column_count=3,
            all_entry_bounds_disjoint_and_in_viewport=True,ascii_only=True,
            all_name_widgets_inside_full_row_not_icon_parent=True,layout=layout))
        setup_name='CXKnockoutSetup'+suffix+'.scr'
        setup=setup_layout((source/('Multiplayer'+suffix+'.scr')).read_bytes())
        payload[setup_name]=setup
        receipt.append(dict(path='Data/Menu/scr/'+setup_name,sha256=hashlib.sha256(setup).hexdigest(),
            bytes=len(setup),reference_size=[w,h],original_setup_composition=True,
            caption='Remis po 2 polowach: zloty gol'))
    dest.mkdir(parents=True)
    for name,raw in payload.items():(dest/name).write_bytes(raw)
    (output/'layout-verification.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps([{k:v for k,v in row.items() if k!='layout'} for row in receipt],indent=2))

if __name__=='__main__':main()
