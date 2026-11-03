/** Own session-only UI state. Team values are actual ETeams animal IDs. */
public final class CXOnlineLobbyModel {
    public static final String VERSION = "GMWL-6fbcaedb-online5";
    public static final int[] TEAM_IDS = {0,1,2,3,4,5,6,7,8,9,10,11,58,37,44,51,30};
    public static final int PAGE_SIZE = 4;
    public static final int RANK_PAGE_SIZE=6, ROOMS=0, RANKING=1, SETTINGS=2;
    public int view=SETTINGS,rankPage;
    public CXOnlineTransport.PlayerStats selfStats;
    public CXOnlineTransport.PlayerStats[] leaderboard;
    public boolean connected, connecting, inRoom, isHost, hostReady, guestReady, started, leaving;
    public int roomId = -1, hostTeam, guestTeam = 1, page, selectedRoom = -1, startMatchId = -1;
    public String roomName = "", hostNick = "", guestNick = "", status = "Wpisz serwer i pseudonim. Wybierz Polacz.", error = "";
    public CXOnlineTransport.Room[] rooms = new CXOnlineTransport.Room[0];

    public static boolean supports(int team) { return CXTeamVisibility.SupportsOnline(team,TEAM_IDS); }
    static int index(int team) { for (int i=0;i<TEAM_IDS.length;i++) if (TEAM_IDS[i]==team) return i; return -1; }
    public static int nextTeam(int team, int delta) {
        return CXTeamVisibility.NextOnline(team,delta,TEAM_IDS);
    }
    public static String clean(String text, int limit) {
        if(text==null)return "";
        StringBuffer out=new StringBuffer();
        for(int i=0;i<text.length()&&out.length()<limit;i++) {
            char c=text.charAt(i); if(c>=32&&c<=126)out.append(c);
        }
        return out.toString().trim();
    }
    public void fail(String message) {
        String text=clean(message,130),lower=text.toLowerCase();
        if(lower.indexOf("different nicknames")>=0||lower.indexOf("nickname")>=0)text="Zmien pseudonim";
        else if(lower.indexOf("version")>=0)text="Inna wersja gry";
        else if(lower.indexOf("timeout")>=0||lower.indexOf("timed out")>=0||lower.indexOf("connection")>=0||lower.indexOf("connectexception")>=0)text="Brak polaczenia";
        else if(lower.indexOf("room full")>=0||lower.indexOf("room not found")>=0||lower.indexOf("not in a room")>=0)text="Pokoj niedostepny";
        error=text;if(error.length()==0)error="Blad polaczenia";
    }
    public void resetRoom() {
        inRoom=false;isHost=false;hostReady=false;guestReady=false;started=false;leaving=false;
        roomId=-1;roomName="";hostNick="";guestNick="";startMatchId=-1;
    }
    public void beginConnect() {
        connected=false;connecting=true;resetRoom();rooms=new CXOnlineTransport.Room[0];
        selectedRoom=-1;page=0;error="";status="Laczenie...";
        selfStats=null;leaderboard=null;rankPage=0;
    }
    public void setLeaderboard(CXOnlineTransport.PlayerStats[] rows) {
        leaderboard=rows;int last=rows==null||rows.length==0?0:(rows.length-1)/RANK_PAGE_SIZE;
        if(rankPage>last)rankPage=last;
    }
    public CXOnlineTransport.PlayerStats rankingAt(int row) {
        int i=rankPage*RANK_PAGE_SIZE+row;return leaderboard!=null&&i>=0&&i<leaderboard.length?leaderboard[i]:null;
    }
    public boolean hasPrevious(){return view==RANKING?rankPage>0:page>0;}
    public boolean hasNext(){return view==RANKING?leaderboard!=null&&(rankPage+1)*RANK_PAGE_SIZE<leaderboard.length:(page+1)*PAGE_SIZE<rooms.length;}
    public void changePage(int delta){
        if(delta<0&&hasPrevious()){if(view==RANKING)rankPage--;else page--;}
        if(delta>0&&hasNext()){if(view==RANKING)rankPage++;else page++;}
    }
    public static String winRate(CXOnlineTransport.PlayerStats row) {
        if(row==null)return "-";
        int value=row.winRate100,whole=value/100,tenth=value/10%10;
        return whole+(tenth==0?"":"."+tenth)+"%";
    }
    public static String summary(CXOnlineTransport.PlayerStats row) {
        return row==null?"W -   R -   P -   WR -":"W "+row.wins+"   R "+row.draws+"   P "+row.losses+"   WR "+winRate(row);
    }
    public void setRooms(CXOnlineTransport.Room[] value) {
        rooms=value==null?new CXOnlineTransport.Room[0]:value;
        int last=rooms.length==0?0:(rooms.length-1)/PAGE_SIZE;if(page>last)page=last;
        boolean selected=false;for(int i=0;i<rooms.length;i++)if(rooms[i].id==selectedRoom)selected=true;
        if(!selected)selectedRoom=-1;
    }
    public CXOnlineTransport.Room roomAt(int row) {
        int i=page*PAGE_SIZE+row;return i>=0&&i<rooms.length?rooms[i]:null;
    }
    public CXOnlineTransport.Room selected() {
        for(int i=0;i<rooms.length;i++)if(rooms[i].id==selectedRoom)return rooms[i];return null;
    }
    public boolean joinable(CXOnlineTransport.Room room) {
        return connected&&!inRoom&&room!=null&&!room.started&&VERSION.equals(room.version)
            && (room.guestNick==null||room.guestNick.length()==0)
            && supports(room.hostTeam)&&supports(room.guestTeam);
    }
    public boolean canReady() {
        return connected&&inRoom&&!started&&!leaving&&supports(hostTeam)&&supports(guestTeam);
    }
    public boolean mineReady() { return isHost?hostReady:guestReady; }
    public void lobby(CXOnlineTransport.Event e) {
        inRoom=true;roomId=e.roomId;roomName=clean(e.roomName,32);isHost=e.isHost;
        hostNick=clean(e.hostNick,20);guestNick=clean(e.guestNick,20);
        hostTeam=e.hostTeam;guestTeam=e.guestTeam;hostReady=e.hostReady;guestReady=e.guestReady;started=e.started;
        error="";
        if(!supports(hostTeam)||!supports(guestTeam))fail("Nieobslugiwana druzyna. Obaj gracze potrzebuja tej samej wersji GMWL.");
        status=guestNick.length()==0?"Oczekiwanie na drugiego gracza...":
            hostReady&&guestReady?"Uruchamianie meczu...":"Wybierz swoja druzyne. Obaj gracze musza wybrac Gotowy.";
    }
    public boolean acceptStart(CXOnlineTransport.Event e) {
        if(!connected||!inRoom||leaving||e.roomId!=roomId||e.matchId==startMatchId)return false;
        if(!VERSION.equals(e.version)||!supports(e.hostTeam)||!supports(e.guestTeam)) {
            fail("Niezgodna wersja lub druzyna. Polaczcie sie z ta sama wersja GMWL.");return false;
        }
        startMatchId=e.matchId;started=true;status="Uruchamianie meczu...";return true;
    }
}
