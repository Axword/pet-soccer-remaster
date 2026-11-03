"""Build own lobby composition from actual Pet Soccer declarations and atlas controls."""
from pathlib import Path
import re,json,hashlib,argparse
HERE=Path(__file__).resolve().parent
GAME=None
DEST=None
REPORT=None

def props(text,x,y,w,h,font,mouse=0):
    return f'''Text("{text}")
TextColor(1.0,1.0,1.0)
Font("{font}")
TextPosFlags(34)
LogicSize({w},{h})
LogicPos({x},{y})
Mouse({mouse})
Keyboard({mouse})
Joy(0)
Visible(1)
CursorVisible(1)
ParentPositioning(1)
ParentCenteringX(0)
ParentCenteringY(0)
ParentSizingX(0)
ParentSizingY(0)'''

def widget(kind,cls,id,text,x,y,w,h,font,extra=''):
    args=f'"{cls}","{id}","Specific"' if kind=='Static' else f'"{cls}","{id}","{text}","Standard","Specific"'
    if kind=='Button':args=f'"{cls}","{id}","{text}","Specific"'
    return kind+'('+args+')\n{\n'+props(text,x,y,w,h,font,0 if kind=='Static' else 1)+'\n'+extra+'\n}\n'

def button(id,text,x,y,w=.19,h=.055,font='FLJazz26'):
    return widget('MenuButton','UIMenuButtonFlying',id,text,x,y,w,h,font,'''Checked(0)
Disabled(0)
CanCallPress(0)
CanCheck(0)
MouseLeaveDestroyFocus(1)
Command(1)
Notify(1)
CanFocus(1)
SelKeyUp(200)
SelKeyDown(208)
CallPressPeriod(0.1)
DoubleClick(0.3)
CheckSound("data/sounds/click")
FocusSound("data/sounds/highlight")
TextureCheckedRect("data/menu/p_menu.png",1024.0,1024.0,203.0,946.0,402.0,992.0)
TextureDisabledRect("data/menu/p_menu.png",1024.0,1024.0,1.0,946.0,200.0,992.0)
TextDisableColor(0.5,0.5,0.5)
TextureRect("data/menu/p_menu.png",1024.0,1024.0,801.0,1.0,1000.0,47.0)''')

def edit(id,text,x,y,w,font):
    return widget('Button','UIEdit',id,text,x,y,w,.047,font,'''Checked(0)
Disabled(0)
CanCallPress(0)
CanCheck(1)
Command(1)
Notify(1)
CanFocus(1)
SelKeyUp(0)
SelKeyDown(0)
MouseLeaveDestroyFocus(1)
CallPressPeriod(0.1)
DoubleClick(0.3)
TextHighLightColor(1.0,1.0,1.0)
TextCheckedColor(1.0,1.0,1.0)
FrameCornerSize(3,3)
TextureRect("data/menu/p_menu.png",1024.0,1024.0,943.0,50.0,950.0,57.0)
TextureCheckedRect("data/menu/p_menu.png",1024.0,1024.0,952.0,50.0,959.0,57.0)''')

def write_scr(path,text,encoding):
    normalized=text.replace('\r\n','\n').replace('\r','\n')
    path.write_bytes(normalized.replace('\n','\r\n').encode(encoding))

def build():
    DEST.mkdir(parents=True,exist_ok=True);report=[]
    for suffix,roman,jazz in [('640','FLRoman16','FLJazz26'),('','FLRoman21','FLJazz32'),('1024','FLRoman28','FLJazz42')]:
        original=(GAME/f'Data/Menu/scr/Main{suffix}.scr').read_text(encoding='cp1250')
        header=original.split('//------ UI stuff')[0]
        root='Interface("UI_CX_ONLINE")\n{\n'+props('',0,0,1,1,roman,1)+'\nCommand(1)\nNotify(1)\nCanFocus(0)\nSelKeyUp(0)\nSelKeyDown(15)\nCursor("data/textures/cursors/cursor.png")\n'
        root=root.replace('ParentPositioning(1)','ParentPositioning(0)',1)
        root+=widget('Static','UIStatic','ID_ONLINE_FRAME','',.04,.20,.92,.68,roman,
            'FrameCornerSize(20,24)\nTextureRect("data/menu/p_menu.png",1024.0,1024.0,262.0,601.0,585.0,921.0)')
        root+='Menu("UIMenu","ID_ACTIONS","Specific")\n{\n'+props('',0,0,1,1,roman,1)+'\nCommand(1)\nNotify(1)\nCanFocus(0)\nSelKeyUp(200)\nSelKeyDown(208)\n'
        def label(id,text,x,y,w,h=.035):return widget('Static','UIStatic',id,text,x,y,w,h,roman)
        def group(id):return 'Menu("UIMenu","'+id+'","Specific")\n{\n'+props('',0,0,1,1,roman,1)+'\nCommand(1)\nNotify(1)\nCanFocus(0)\nSelKeyUp(200)\nSelKeyDown(208)\n'
        root+=group('ID_TABS')
        root+=button('ID_TAB_ROOMS','Pokoje',.08,.23,.21,.06,jazz)+button('ID_TAB_RANKING','Ranking',.32,.23,.22,.06,jazz)
        root+=button('ID_SETTINGS','Ustawienia',.69,.23,.23,.06,jazz)+'}\n'
        root+=group('ID_SUMMARY')+label('ID_SELF_STATS','W -   R -   P -   WR -',.08,.31,.54,.04)+label('ID_CONNECTION','',.67,.31,.25,.04)+'}\n'
        root+=group('ID_ROOMS_VIEW')
        for i in range(4):root+=button('ID_ROOM_'+str(i),'',.08,.40+i*.068,.84,.055,roman)
        root+=label('ID_EMPTY_ROOMS','',.08,.44,.84,.04)
        root+=button('ID_REFRESH','Odswiez',.08,.725,.18,.055,jazz)+edit('ID_ROOM_NAME','Mecz 1v1',.29,.73,.24,roman)
        root+=button('ID_CREATE','Utworz',.55,.725,.18,.055,jazz)+button('ID_JOIN','Dolacz',.75,.725,.17,.055,jazz)+'}\n'
        root+=group('ID_RANKING_VIEW')
        columns=[('NICK','Gracz',.08,.40),('W','W',.49,.10),('D','R',.60,.10),('L','P',.71,.10),('WR','WR',.82,.10)]
        for key,title,x,w in columns:root+=label('ID_RANK_HEADER_'+key,title,x,.385,w,.04)
        for row in range(6):
            for key,title,x,w in columns:root+=label('ID_RANK_'+str(row)+'_'+key,'',x,.44+row*.055,w,.04)
        root+='}\n'
        root+=group('ID_SETTINGS_VIEW')
        root+=label('ID_SERVER_LABEL','Serwer',.10,.40,.22,.045)+edit('ID_SERVER','127.0.0.1',.36,.395,.54,roman)
        root+=label('ID_PORT_LABEL','Port',.10,.49,.22,.045)+edit('ID_PORT','27888',.36,.485,.20,roman)
        root+=label('ID_NICK_LABEL','Pseudonim',.10,.58,.22,.045)+edit('ID_NICK','Player',.36,.575,.54,roman)
        root+=button('ID_CONNECT','Polacz',.38,.70,.24,.06,jazz)+'}\n'
        root+=group('ID_LOBBY_VIEW')
        root+=label('ID_HOST','',.10,.38,.34,.045)+label('ID_GUEST','',.56,.38,.34,.045)
        root+=label('ID_HOST_READY','',.10,.44,.34,.04)+label('ID_GUEST_READY','',.56,.44,.34,.04)
        root+=label('ID_HOST_TEAM','',.125,.54,.31,.05)+label('ID_GUEST_TEAM','',.565,.54,.31,.05)
        root+=button('ID_HOST_PREV','<',.065,.54,.055,.05,jazz)+button('ID_HOST_NEXT','>',.44,.54,.055,.05,jazz)
        root+=button('ID_GUEST_PREV','<',.505,.54,.055,.05,jazz)+button('ID_GUEST_NEXT','>',.88,.54,.055,.05,jazz)
        root+=button('ID_READY','Gotowy',.37,.70,.26,.06,jazz)+'}\n'
        root+=button('ID_PAGE_PREV','<',.77,.80,.06,.045,jazz)+button('ID_PAGE_NEXT','>',.87,.80,.06,.045,jazz)
        root+=label('ID_ERROR','',.08,.838,.84,.03).replace('TextColor(1.0,1.0,1.0)','TextColor(1.0,0.65,0.3)')
        root+=button('ID_BACK','Wroc',.375,.91,.25,.065,jazz)
        root+='}\n}\n'
        target=DEST/f'CXOnline{suffix}.scr';write_scr(target,header+'// Own Online lobby; original atlas, fonts and native controls.\n'+root,'ascii')
        # Clone a real stock button with all native component settings intact.
        match=re.search(r'      MenuButton\("UIMenuButtonFlying","ID_MULTIPLAYER".*?\n      \}// \[UIMenuButtonFlying\] ID_MULTIPLAYER',original,re.S)
        assert match,'Expected current main menu multiplayer button'
        online=match.group(0).replace('ID_MULTIPLAYER','ID_CX_ONLINE').replace('&&MenuMainMultiplayer&&','Online').replace('LogicPos(0.0,0.45)','LogicPos(0.0,0.60)')
        changed=original if '"ID_CX_ONLINE"' in original else original[:match.end()]+'\n\n'+online+original[match.end():]
        write_scr(DEST/f'Main{suffix}.scr',changed,'cp1250')
        # A noninteractive HUD, separate from menus; original atlas and fonts.
        pause='Interface("UI_CX_ONLINE_PAUSE")\n{\n'+props('',0,0,1,1,roman,0)
        pause=pause.replace('ParentPositioning(1)','ParentPositioning(0)',1)
        pause=pause.replace('CursorVisible(1)','CursorVisible(0)',1)
        pause+='\nCommand(0)\nNotify(0)\nCanFocus(0)\n'
        pause+=widget('Static','UIStatic','ID_ONLINE_PAUSE_FRAME','',.34,.35,.32,.21,roman,
            'FrameCornerSize(16,18)\nTextureRect("data/menu/p_menu.png",1024.0,1024.0,262.0,601.0,585.0,921.0)')
        pause+=widget('Static','UIStatic','ID_ONLINE_PAUSE_TITLE','PRZERWA',.36,.385,.28,.06,roman)
        pause+=widget('Static','UIStatic','ID_ONLINE_PAUSE_TIME','15',.36,.465,.28,.06,roman)
        pause+='}\n'
        write_scr(DEST/f'CXOnlinePause{suffix}.scr',header+'// Own Online pause HUD; no input or menu state.\n'+pause,'ascii')
        report.append({'source':str(GAME/f'Data/Menu/scr/Main{suffix}.scr'),'source_sha256':hashlib.sha256(original.encode('cp1250')).hexdigest(),'new_scr':str(target),'entry':'ID_CX_ONLINE','atlas':'data/menu/p_menu.png','fonts':[roman,jazz],'existing_main_buttons_preserved':True})
    REPORT.write_text(json.dumps(report,indent=2)+'\n','utf8')
    print('Wrote nine SCR overlays; current source untouched.')
def main():
    global GAME,DEST,REPORT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True,help='Read-only reconstructed GMWL game directory')
    parser.add_argument('--output',type=Path,required=True,help='Fresh local overlay directory')
    args=parser.parse_args()
    GAME=args.game.resolve()
    output=args.output.resolve()
    if output.exists() or output.is_relative_to(GAME):parser.error('Fresh output outside the input game required')
    DEST=output/'Data/Menu/scr'
    REPORT=output/'scr-mapping.json'
    build()

if __name__=='__main__':main()
