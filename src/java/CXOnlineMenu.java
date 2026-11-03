/** Own nonblocking lobby UI using the original Pet Soccer SCR controls and atlas. */
public class CXOnlineMenu extends SoccerUserInterface {
    public static final int UI_ONLINE = 20;
    public final CXOnlineLobbyModel state = new CXOnlineLobbyModel();
    static CXOnlineMenu current;
    boolean showing;
    String savedServer="127.0.0.1", savedPort="27888", savedNick="", savedRoom="Mecz 1v1";

    public CXOnlineMenu() {
        super();m_sTitle="ONLINE";
        m_sFiles=new String[]{"data/menu/scr/CXOnline640.scr","data/menu/scr/CXOnline.scr","data/menu/scr/CXOnline1024.scr"};
    }
    public static CXOnlineMenu Current() { return current; }
    public static void Quiet(UIWindow root) { CXOnlineVisibility.quiet(root); }
    public static void Forget(UIWindow root) { CXOnlineVisibility.forget(root); }
    public static void SuspendAll(SoccerMainMenuModule module) { CXOnlineVisibility.all(module); }
    public static void Open(SoccerMainMenuModule module) {
        if(module==null)return;
        SuspendAll(module);module.ShowUI(UI_ONLINE);
    }
    public static boolean HandleMain(MenuMain source, UIWindow control, int command) {
        if(control==null||!"ID_CX_ONLINE".equals(control.m_sId))return false;
        if(command==0)Open((SoccerMainMenuModule)source.m_module);
        return true;
    }
    public static void MainInit(MenuMain source) {
        UIWindow control=source.GetElem("ID_CX_ONLINE");if(control!=null)source.AddToSlideIn(control,0.4f);
    }
    public static boolean LoadUI(SoccerMainMenuModule module,int id) {
        if(id!=UI_ONLINE)return false;
        SoccerUserInterface ui=(SoccerUserInterface)module.CreateObject("CXOnlineMenu");
        if(ui==null)throw new IllegalStateException("Unable to create Online UI");
        Vector cursor=null;int previous=SoccerMainMenuModule.m_nCurUI;
        if(previous>=0&&previous<module.m_tUIs.length&&module.m_tUIs[previous]!=null)
            cursor=module.m_tUIs[previous].GetCursorPos();
        if(cursor==null)cursor=new Vector(GameObject.GetScreenWidth()/2.0f,GameObject.GetScreenHeight()/2.0f,0.0f);
        ui.SetInitialCursorPos(cursor);
        if(!ui.Load(module,SoccerGame.GetResolution()))throw new IllegalStateException("Unable to load Online SCR");
        module.m_tUIs[id]=ui;ui.MoveTop();return true;
    }
    public void OnInit() {
        super.OnInit();current=this;ProcessKb(true);
        PlayerSave user=CoreLogic.GetPlayer();
        if(savedNick.length()==0)savedNick=CXOnlineLobbyModel.clean(user==null?"Player":user.m_Name,20);
        if(savedNick.length()==0)savedNick="Player";
        edit("ID_SERVER",savedServer);edit("ID_PORT",savedPort);edit("ID_NICK",savedNick);edit("ID_ROOM_NAME",savedRoom);
    }
    public void Show() {
        if(!CXOnlineVisibility.show(this)){showing=false;return;}
        CXTeamVisibility.Reload();
        current=this;showing=true;m_sTitle="ONLINE";super.Show();ProcessKb(true);
        if(state.connected){CXOnlineTransport.listRooms();CXOnlineTransport.requestSelfStats();if(state.view==CXOnlineLobbyModel.RANKING)CXOnlineTransport.requestLeaderboard();}
        else state.view=CXOnlineLobbyModel.SETTINGS;
        Render();
    }
    public void MoveTop() {super.MoveTop();StackContent();}
    public void Hide() { rememberEdits();showing=false;DisableCallMethod("Show");super.Hide(); }
    /** Native MoveTop moves one window/frame, not its control descendants. */
    void moveTree(UIWindow window) {
        if(window==null||!window.m_bVisible)return;window.MoveTop();
        if(window.m_vChildWindows!=null)for(int i=0;i<window.m_vChildWindows.size();i++)
            moveTree((UIWindow)window.m_vChildWindows.elementAt(i));
    }
    void StackContent() {
        if(!showing)return;
        UIWindow frame=GetElem("ID_ONLINE_FRAME");if(frame!=null)frame.MoveTop();
        moveTree(GetElem("ID_ACTIONS"));
        if(m_currCursor!=null)m_currCursor.MoveTop();
    }
    public static void Pump() {
        CXOnlineMenu menu=current;if(menu==null)return;
        CXOnlineTransport.Event[] events=CXOnlineTransport.drainEvents();
        for(int i=0;i<events.length;i++)menu.Handle(events[i]);
        if(events.length>0&&menu.showing)menu.Render();
    }
    void Handle(CXOnlineTransport.Event e) {
        if(e==null)return;
        if(e.type==CXOnlineTransport.DISCONNECTED||e.type==CXOnlineTransport.ERROR||e.type==CXOnlineTransport.LEFT)CXOnlineMatch.handle(e);
        if(e.type==CXOnlineTransport.CONNECTING) {state.connecting=true;state.status="Laczenie...";}
        else if(e.type==CXOnlineTransport.CONNECTED) {
            state.connected=true;state.connecting=false;state.error="";state.status="Polaczono";state.view=CXOnlineLobbyModel.ROOMS;
            CXOnlineTransport.listRooms();CXOnlineTransport.requestSelfStats();
        } else if(e.type==CXOnlineTransport.ERROR) {
            state.connecting=false;state.leaving=false;state.connected=CXOnlineTransport.isConnected();
            if(!state.connected) {state.resetRoom();state.setRooms(null);state.status="Blad polaczenia. Sprawdz serwer i wybierz Polacz.";}
            state.fail(e.message);
        }
        else if(e.type==CXOnlineTransport.DISCONNECTED) {
            state.connected=false;state.connecting=false;state.resetRoom();state.setRooms(null);
            state.status="Rozlaczono";if(!"Stopped".equals(e.message))state.fail(e.message);
        } else if(e.type==CXOnlineTransport.ROOMS) {
            state.setRooms(e.rooms);if(!state.inRoom)state.status=state.rooms.length==0?"Brak pokoi. Utworz nowy pokoj.":"Wybierz otwarty pokoj i Dolacz.";
        } else if(e.type==CXOnlineTransport.LOBBY)state.lobby(e);
        else if(e.type==CXOnlineTransport.LEFT) {state.resetRoom();state.status="Polaczono";CXOnlineTransport.listRooms();CXOnlineTransport.requestSelfStats();}
        else if(e.type==CXOnlineTransport.START&&state.acceptStart(e)) {
            CXOnlineMatch.start((SoccerMainMenuModule)m_module,e.isHost,e.hostTeam,e.guestTeam);
        }
        else if(e.type==CXOnlineTransport.LEADERBOARD)state.setLeaderboard(e.leaderboard);
        else if(e.type==CXOnlineTransport.SELF_STATS)state.selfStats=e.playerStats;
        else if(e.type==CXOnlineTransport.RESULT&&e.resultStatus==2){CXOnlineTransport.requestSelfStats();CXOnlineTransport.requestLeaderboard();}
    }
    public void Connect() {
        rememberEdits();String server=CXOnlineLobbyModel.clean(savedServer,100),nick=CXOnlineLobbyModel.clean(savedNick,20);
        int port;try {port=Integer.parseInt(savedPort.trim());}catch(Exception invalid){state.fail("Nieprawidlowy port");Render();return;}
        if(server.length()==0||nick.length()==0||port<1||port>65535) {state.fail("Sprawdz adres, port i pseudonim");Render();return;}
        state.beginConnect();CXOnlineTransport.start(server,port,nick,CXOnlineLobbyModel.VERSION);Render();
    }
    public void CreateRoom() {
        if(!state.connected||state.inRoom)return;rememberEdits();
        String name=CXOnlineLobbyModel.clean(savedRoom,32);if(name.length()==0)name="Mecz 1v1";
        state.error="";state.status="Tworzenie pokoju...";CXOnlineTransport.createRoom(name);Render();
    }
    public void JoinRoom(int roomId) {
        for(int i=0;i<state.rooms.length;i++)if(state.rooms[i].id==roomId)state.selectedRoom=roomId;
        if(!state.joinable(state.selected())) {state.fail("Pokoj niedostepny");Render();return;}
        state.error="";state.status="Dolaczanie do pokoju...";CXOnlineTransport.joinRoom(roomId);Render();
    }
    public void ToggleReady() {
        if(!state.canReady())return;state.error="";state.status="Wysylanie gotowosci...";
        CXOnlineTransport.setReady(!state.mineReady());Render();
    }
    public void ChangeTeam(int delta) {
        if(!state.inRoom||state.started||state.mineReady())return;
        int host=state.hostTeam,guest=state.guestTeam;
        if(state.isHost)host=CXOnlineLobbyModel.nextTeam(host,delta);else guest=CXOnlineLobbyModel.nextTeam(guest,delta);
        CXOnlineTransport.setTeams(host,guest);
    }
    public void Back() {
        if(state.inRoom) {if(!state.leaving){state.leaving=true;CXOnlineTransport.leaveRoom();}state.status="Opuszczanie pokoju...";Render();return;}
        if(state.view==CXOnlineLobbyModel.SETTINGS&&state.connected){SelectView(CXOnlineLobbyModel.ROOMS);return;}
        CXOnlineTransport.stop();state.connected=false;state.connecting=false;state.resetRoom();state.setRooms(null);
        SuspendAll((SoccerMainMenuModule)m_module);((SoccerMainMenuModule)m_module).ShowUI(0);
    }
    public void SelectView(int view) {
        if(state.inRoom)return;rememberEdits();state.view=view;state.error="";
        if(view==CXOnlineLobbyModel.RANKING&&state.connected){CXOnlineTransport.requestLeaderboard();CXOnlineTransport.requestSelfStats();}
        Render();
    }
    public void ShowRanking(){SelectView(CXOnlineLobbyModel.RANKING);}
    public void ShowRooms(){SelectView(CXOnlineLobbyModel.ROOMS);}
    public void ShowSettings(){SelectView(CXOnlineLobbyModel.SETTINGS);}
    public void RefreshLeaderboard(){if(state.connected){CXOnlineTransport.requestLeaderboard();CXOnlineTransport.requestSelfStats();}}
    public void ConfigureConnection(String host,int port,String nick){
        savedServer=host;savedPort=""+port;savedNick=nick;
        edit("ID_SERVER",host);edit("ID_PORT",savedPort);edit("ID_NICK",nick);
    }
    public void OnUICommand(UIWindow control,int command) {
        if(!showing||control==null||!control.m_bVisible)return;super.OnUICommand(control,command);String id=control.m_sId;
        if(command==3) {rememberEdits();if("ID_SERVER".equals(id)||"ID_PORT".equals(id)||"ID_NICK".equals(id))Connect();return;}
        if(command!=0)return;
        if("ID_CONNECT".equals(id))Connect();else if("ID_REFRESH".equals(id))CXOnlineTransport.listRooms();
        else if("ID_CREATE".equals(id))CreateRoom();else if("ID_JOIN".equals(id))JoinRoom(state.selectedRoom);
        else if("ID_READY".equals(id))ToggleReady();else if("ID_BACK".equals(id))Back();
        else if("ID_TAB_ROOMS".equals(id))SelectView(CXOnlineLobbyModel.ROOMS);
        else if("ID_TAB_RANKING".equals(id))SelectView(CXOnlineLobbyModel.RANKING);
        else if("ID_SETTINGS".equals(id))SelectView(state.view==CXOnlineLobbyModel.SETTINGS?CXOnlineLobbyModel.ROOMS:CXOnlineLobbyModel.SETTINGS);
        else if("ID_HOST_PREV".equals(id)||"ID_GUEST_PREV".equals(id))ChangeTeam(-1);
        else if("ID_HOST_NEXT".equals(id)||"ID_GUEST_NEXT".equals(id))ChangeTeam(1);
        else if("ID_PAGE_PREV".equals(id)) {state.changePage(-1);Render();}
        else if("ID_PAGE_NEXT".equals(id)) {state.changePage(1);Render();}
        else if(id!=null&&id.startsWith("ID_ROOM_")) {
            try {CXOnlineTransport.Room room=state.roomAt(Integer.parseInt(id.substring(8)));if(room!=null)state.selectedRoom=room.id;}catch(Exception invalid){}
            Render();
        }
    }
    void OnKeyPressed(int key,char character) {if(showing&&key==1)Back();}
    void rememberEdits() {
        savedServer=value("ID_SERVER",savedServer);savedPort=value("ID_PORT",savedPort);
        savedNick=value("ID_NICK",savedNick);savedRoom=value("ID_ROOM_NAME",savedRoom);
    }
    String value(String id,String fallback) {UIWindow e=GetElem(id);return e instanceof UIEdit?((UIEdit)e).m_sEditText:fallback;}
    void edit(String id,String text) {UIWindow e=GetElem(id);if(e instanceof UIEdit)((UIEdit)e).SetText(text);}
    void text(String id,String text) {
        UIWindow e=GetElem(id);if(!(e instanceof UIStatic))return;
        UIStatic widget=(UIStatic)e;float width=widget.GetSize().fX-4.0f;
        String fitted=text;Vector extent=widget.GetTextExtent(fitted);
        while(width>4.0f&&extent!=null&&extent.fX>width&&text.length()>1) {
            text=text.substring(0,text.length()-1);fitted=text+"...";extent=widget.GetTextExtent(fitted);
        }
        widget.SetText(fitted);if(showing&&widget.m_bVisible)widget.OnDisplayText();
    }
    void disable(String id,boolean disabled) {UIWindow e=GetElem(id);if(e instanceof UIButton)((UIButton)e).SetDisabled(disabled);}
    void visibleTree(UIWindow node,boolean visible) {
        if(node==null)return;if(visible)node.Show();else{CXOnlineVisibility.cancel(node);node.Hide();}
        if(node.m_vChildWindows!=null)for(int i=0;i<node.m_vChildWindows.size();i++)visibleTree((UIWindow)node.m_vChildWindows.elementAt(i),visible);
    }
    void visible(String id,boolean show) {visibleTree(GetElem(id),showing&&show);}
    String team(int id) {TeamData data=CXOnlineLobbyModel.supports(id)?ETeams.GetTeamData(id):null;return data==null?"Nieznana druzyna":data.m_sName;}
    public void Render() {
        if(!showing||GetElem("ID_SELF_STATS")==null)return;
        boolean lobby=state.inRoom,rooms=!lobby&&state.view==CXOnlineLobbyModel.ROOMS;
        boolean ranking=!lobby&&state.view==CXOnlineLobbyModel.RANKING,settings=!lobby&&state.view==CXOnlineLobbyModel.SETTINGS;
        visible("ID_TABS",!lobby);visible("ID_SUMMARY",!lobby);visible("ID_ROOMS_VIEW",rooms);
        visible("ID_RANKING_VIEW",ranking);visible("ID_SETTINGS_VIEW",settings);visible("ID_LOBBY_VIEW",lobby);
        visible("ID_PAGE_PREV",rooms||ranking);visible("ID_PAGE_NEXT",rooms||ranking);
        text("ID_SELF_STATS",CXOnlineLobbyModel.summary(state.selfStats));
        text("ID_CONNECTION",state.connecting?"Laczenie...":state.connected?"Polaczono":"Rozlaczono");
        text("ID_ERROR",state.error);visible("ID_ERROR",state.error.length()>0);
        disable("ID_TAB_ROOMS",state.view==CXOnlineLobbyModel.ROOMS);disable("ID_TAB_RANKING",state.view==CXOnlineLobbyModel.RANKING);
        disable("ID_CONNECT",state.connecting);disable("ID_SERVER",state.connecting);disable("ID_PORT",state.connecting);disable("ID_NICK",state.connecting);
        disable("ID_REFRESH",!state.connected);disable("ID_CREATE",!state.connected);disable("ID_ROOM_NAME",!state.connected);
        disable("ID_JOIN",!state.joinable(state.selected()));
        disable("ID_PAGE_PREV",!state.hasPrevious());disable("ID_PAGE_NEXT",!state.hasNext());
        for(int i=0;i<CXOnlineLobbyModel.PAGE_SIZE;i++) {
            CXOnlineTransport.Room room=state.roomAt(i);String line="";
            if(room!=null)line=(room.id==state.selectedRoom?"> ":"")+CXOnlineLobbyModel.clean(room.name,30)+
                (room.started?"  [Mecz]":room.guestNick!=null&&room.guestNick.length()>0?"  [Pelny]":!CXOnlineLobbyModel.VERSION.equals(room.version)?"  [Wersja]":"");
            text("ID_ROOM_"+i,line);visible("ID_ROOM_"+i,rooms&&room!=null);disable("ID_ROOM_"+i,!state.connected||room==null);
        }
        text("ID_EMPTY_ROOMS",state.connected&&state.rooms.length==0?"Brak pokoi":"");
        for(int i=0;i<CXOnlineLobbyModel.RANK_PAGE_SIZE;i++) {
            CXOnlineTransport.PlayerStats row=state.rankingAt(i);String prefix="ID_RANK_"+i+"_";
            text(prefix+"NICK",row==null?"":CXOnlineLobbyModel.clean(row.nick,20));
            text(prefix+"W",row==null?"":""+row.wins);text(prefix+"D",row==null?"":""+row.draws);
            text(prefix+"L",row==null?"":""+row.losses);text(prefix+"WR",row==null?"":CXOnlineLobbyModel.winRate(row));
        }
        text("ID_HOST",state.hostNick);text("ID_GUEST",state.guestNick.length()==0?"-":state.guestNick);
        text("ID_HOST_TEAM",team(state.hostTeam));text("ID_GUEST_TEAM",team(state.guestTeam));
        text("ID_HOST_READY",state.hostReady?"Gotowy":"");text("ID_GUEST_READY",state.guestReady?"Gotowy":"");
        visible("ID_HOST_PREV",lobby&&state.isHost);visible("ID_HOST_NEXT",lobby&&state.isHost);
        visible("ID_GUEST_PREV",lobby&&!state.isHost);visible("ID_GUEST_NEXT",lobby&&!state.isHost);
        boolean lock=!state.canReady()||state.mineReady();disable("ID_HOST_PREV",lock);disable("ID_HOST_NEXT",lock);disable("ID_GUEST_PREV",lock);disable("ID_GUEST_NEXT",lock);
        text("ID_READY",state.mineReady()?"Anuluj":"Gotowy");disable("ID_READY",!state.canReady());
        text("ID_BACK",lobby?"Opusc":"Wroc");disable("ID_BACK",state.leaving);StackContent();
    }
}
