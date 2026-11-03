import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.util.Vector;

/** Java 1.3 compatible, engine-independent relay transport. No network I/O on caller thread. */
public final class CXOnlineTransport {
    public static final int CONNECTING=1, CONNECTED=2, DISCONNECTED=3, ERROR=4,
        ROOMS=5, LOBBY=6, LEFT=7, START=8, SNAPSHOT=9, INPUT=10,
        LEADERBOARD=11, SELF_STATS=12, RESULT=13, PAUSE=14;
    public static final int DEFAULT_PORT=27888;
    public static final String DEFAULT_VERSION="GMWL-6fbcaedb-online4";
    private static final int W_HELLO=1,W_WELCOME=2,W_LIST=3,W_ROOMS=4,W_CREATE=5,
        W_JOIN=6,W_LEAVE=7,W_READY=8,W_LOBBY=9,W_LEFT=10,W_ERROR=11,
        W_SNAPSHOT=12,W_INPUT=13,W_PING=14,W_PONG=15,W_TEAMS=16,W_START=17,
        W_GET_LEADERBOARD=18,W_LEADERBOARD=19,W_GET_SELF_STATS=20,W_SELF_STATS=21,
        W_RESULT=22,W_RESULT_STATUS=23,W_PAUSE_REQUEST=24,W_PAUSE_STATE=25;
    private static final int MAX_FRAME=65536, MAX_DATA=60000, MAX_QUEUE=64, MAX_BYTES=131072;
    private static volatile Session current;
    private static Connector pendingConnector;
    private static final Object CONNECT_LOCK=new Object();

    public static final class Room {
        public int id,hostTeam,guestTeam,matchId;
        public String name,version,hostNick,guestNick;
        public boolean hostReady,guestReady,started;
    }
    public static final class PlayerStats {
        public String nick;
        public int rank,wins,draws,losses,games,points,winRate100;
    }
    public static final class Event {
        public int type,roomId,matchId,hostTeam,guestTeam,resultStatus,remainingMillis;
        public String message,roomName,version,hostNick,guestNick;
        public boolean hostReady,guestReady,isHost,started,paused;
        public Room[] rooms;
        public PlayerStats[] leaderboard;
        public PlayerStats playerStats;
        public byte[] data;
        Event(int value,String text) { type=value; message=text; }
    }

    private CXOnlineTransport() {}

    public static synchronized void start(String server,int port,String nick,String version) {
        if(current!=null) current.running=false;
        Session s=new Session(server,port,nick,version);
        current=s;
        if(server==null || server.length()==0 || server.length()>255 || port<1 || port>65535
            || !validText(nick,48) || !validText(version,80)) {
            s.running=false;
            s.emit(new Event(ERROR,"Invalid server, port, nickname or version"));
            return;
        }
        Thread thread=new Thread(s,"Online relay reader");
        thread.setDaemon(true);
        thread.start();
    }

    public static synchronized void stop() {
        if(current!=null) {
            current.running=false;
            current.connected=false;
            current.resetRoom();
            current.emit(new Event(DISCONNECTED,"Stopped"));
        }
    }
    public static synchronized boolean isConnected() { return current!=null && current.connected; }
    public static synchronized boolean isHost() { return current!=null && current.roomId!=0 && current.host; }
    public static synchronized boolean isGuest() { return current!=null && current.roomId!=0 && !current.host; }
    public static synchronized boolean isMatchStarted() { return current!=null && current.started; }
    public static synchronized int getRoomId() { return current==null?0:current.roomId; }
    public static synchronized int getMatchId() { return current==null?0:current.matchId; }
    public static synchronized int getHostTeam() { return current==null?0:current.hostTeam; }
    public static synchronized int getGuestTeam() { return current==null?1:current.guestTeam; }
    /** Queue only; both participants wait for the server's authoritative state. */
    public static synchronized boolean requestPause() {
        if(current==null || !current.connected || !current.started || current.matchId<=0) return false;
        if(current.pauseRemaining()>0) return true;
        long now=System.currentTimeMillis();
        if(current.lastPauseRequest!=0 && now>=current.lastPauseRequest && now-current.lastPauseRequest<1000) return true;
        if(!current.enqueue(W_PAUSE_REQUEST,new byte[0])) return false;
        current.lastPauseRequest=now;
        return true;
    }
    /** Cache-only countdown: never block the engine thread or wait for the network. */
    public static synchronized boolean isPaused() { return current!=null && current.pauseRemaining()>0; }
    public static synchronized int getPauseRemainingMillis() { return current==null?0:current.pauseRemaining(); }
    public static synchronized int getPauseMatchId() {
        return current!=null && current.connected && current.started && current.pauseMatchId==current.matchId?current.pauseMatchId:0;
    }
    /** Null means no response from this connection yet; an empty array is a real empty ranking. */
    public static synchronized PlayerStats[] getLeaderboard() { return current==null?null:copyStats(current.leaderboard); }
    public static synchronized PlayerStats getSelfStats() { return current==null?null:copyStats(current.selfStats); }
    /** Repeated UI requests merge into one deferred refresh, paced by the writer. */
    public static synchronized void requestLeaderboard() { if(current!=null) current.requestStats(true); }
    public static synchronized void requestSelfStats() { if(current!=null) current.requestStats(false); }
    /** 0 unknown, 1 awaiting other peer, 2 durably recorded, 3 conflicting attestations. */
    public static synchronized int getResultStatus(int matchId) {
        return current!=null && current.resultMatchId==matchId?current.resultStatus:0;
    }
    public static synchronized boolean submitMatchResult(int matchId,int hostGoals,int guestGoals) {
        if(current==null || !current.started || current.matchId!=matchId || matchId<=0
            || hostGoals<0 || hostGoals>999 || guestGoals<0 || guestGoals>999) return false;
        return current.enqueue(W_RESULT,integers(new int[]{matchId,hostGoals,guestGoals}));
    }
    public static void listRooms() { command(W_LIST,new byte[0]); }
    public static void leaveRoom() { command(W_LEAVE,new byte[0]); }
    public static void createRoom(String name) {
        try { if(!validText(name,96)) throw new IOException("Invalid room name"); command(W_CREATE,textBytes(name)); }
        catch(IOException ex) { localError(ex.toString()); }
    }
    public static void joinRoom(int id) { command(W_JOIN,integers(new int[]{id})); }
    public static void setReady(boolean ready) { command(W_READY,new byte[]{(byte)(ready?1:0)}); }
    public static void setTeams(int hostTeam,int guestTeam) {
        if(!validTeam(hostTeam) || !validTeam(guestTeam)) { localError("Invalid team"); return; }
        command(W_TEAMS,integers(new int[]{hostTeam,guestTeam}));
    }
    public static synchronized boolean sendSnapshot(byte[] data) {
        return current!=null && current.started && current.host && current.enqueue(W_SNAPSHOT,data);
    }
    /** Terminal state is a FIFO control-order packet and must precede submitMatchResult. */
    public static synchronized boolean sendFinalSnapshot(byte[] data) {
        if(current==null || !current.started || !current.host || data==null || data.length<1) return false;
        if(!current.enqueueOrdered(W_SNAPSHOT,data)) return false;
        current.outgoingSnapshot=null;
        return true;
    }
    public static synchronized boolean sendInput(byte[] data) {
        return current!=null && current.started && !current.host && current.enqueue(W_INPUT,data);
    }
    /** Integer input packet: count (int32), followed by count int32 values; maximum 32. */
    public static boolean sendInput(int[] values) {
        if(values==null || values.length<1 || values.length>32) return false;
        int[] packet=new int[values.length+1];
        packet[0]=values.length;
        System.arraycopy(values,0,packet,1,values.length);
        return sendInput(integers(packet));
    }
    public static synchronized byte[] pollSnapshot() {
        if(current==null) return null;
        byte[] data=current.snapshot;
        current.snapshot=null;
        return data;
    }
    public static synchronized byte[] pollInputBytes() {
        if(current==null || current.inputs.size()==0) return null;
        byte[] data=(byte[])current.inputs.elementAt(0);
        current.inputs.removeElementAt(0);
        return data;
    }
    public static int[] pollInput() {
        byte[] data=pollInputBytes();
        if(data==null) return null;
        try {
            DataInputStream in=new DataInputStream(new ByteArrayInputStream(data));
            int count=in.readInt();
            if(count<1 || count>32 || data.length!=4+count*4) throw new IOException("Invalid input packet");
            int[] values=new int[count];
            for(int n=0;n<count;n++) values[n]=in.readInt();
            return values;
        } catch(IOException ex) { localError(ex.toString()); return null; }
    }
    public static synchronized Event[] drainEvents() {
        if(current==null) return new Event[0];
        Event[] events=new Event[current.events.size()];
        current.events.copyInto(events);
        current.events.removeAllElements();
        return events;
    }

    private static synchronized void command(int kind,byte[] body) {
        if(current!=null && !current.enqueue(kind,body)) current.emit(new Event(ERROR,"Not connected or outbound queue full"));
    }
    private static synchronized void localError(String message) {
        if(current!=null) current.emit(new Event(ERROR,message));
    }
    private static boolean validText(String value,int limit) {
        if(value==null || value.length()==0) return false;
        for(int i=0;i<value.length();i++) if(value.charAt(i)<32 || value.charAt(i)==127) return false;
        try { return value.getBytes("UTF-8").length<=limit; } catch(IOException ex) { return false; }
    }
    private static PlayerStats copyStats(PlayerStats value) {
        if(value==null) return null;
        PlayerStats out=new PlayerStats();out.nick=value.nick;out.rank=value.rank;
        out.wins=value.wins;out.draws=value.draws;out.losses=value.losses;out.games=value.games;
        out.points=value.points;out.winRate100=value.winRate100;return out;
    }
    private static PlayerStats[] copyStats(PlayerStats[] values) {
        if(values==null) return null;
        PlayerStats[] out=new PlayerStats[values.length];
        for(int i=0;i<out.length;i++) out[i]=copyStats(values[i]);
        return out;
    }
    private static boolean validTeam(int team) { return (team>=0 && team<=11) || team==30 || team==37 || team==44 || team==51 || team==58; }
    private static byte[] textBytes(String text) throws IOException {
        byte[] value=text.getBytes("UTF-8");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        DataOutputStream out=new DataOutputStream(bytes);
        out.writeShort(value.length); out.write(value); out.flush();
        return bytes.toByteArray();
    }
    private static byte[] integers(int[] values) {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        DataOutputStream out=new DataOutputStream(bytes);
        try { for(int n=0;n<values.length;n++) out.writeInt(values[n]); out.flush(); }
        catch(IOException impossible) {}
        return bytes.toByteArray();
    }
    private static String readText(DataInputStream in) throws IOException {
        int size=in.readUnsignedShort();
        if(size>1024 || size>in.available()) throw new IOException("Invalid text length");
        byte[] data=new byte[size]; in.readFully(data);
        return new String(data,"UTF-8");
    }
    private static Room readRoom(DataInputStream in) throws IOException {
        Room room=new Room();
        room.id=in.readInt();room.name=readText(in);room.version=readText(in);
        room.hostNick=readText(in);room.guestNick=readText(in);
        room.hostReady=in.readBoolean();room.guestReady=in.readBoolean();room.started=in.readBoolean();
        room.hostTeam=in.readInt();room.guestTeam=in.readInt();room.matchId=in.readInt();
        if(!validTeam(room.hostTeam) || !validTeam(room.guestTeam)) throw new IOException("Invalid lobby team");
        return room;
    }
    private static PlayerStats readStats(DataInputStream in) throws IOException {
        PlayerStats value=new PlayerStats();value.nick=readText(in);value.rank=in.readInt();
        value.wins=in.readInt();value.draws=in.readInt();value.losses=in.readInt();
        value.games=in.readInt();value.points=in.readInt();value.winRate100=in.readInt();
        if(!validText(value.nick,48) || value.rank<0 || value.wins<0 || value.draws<0 || value.losses<0
            || value.games<0 || value.points<0 || value.winRate100<0 || value.winRate100>10000
            || (long)value.wins+value.draws+value.losses!=value.games
            || 3L*value.wins+value.draws!=value.points
            || value.winRate100!=(value.games==0?0:(int)(10000L*value.wins/value.games)))
            throw new IOException("Invalid player statistics");
        return value;
    }
    private static void sleep(long millis) { try { Thread.sleep(millis); } catch(InterruptedException ex) {} }

    /** Java 1.3 has no Socket.connect(address,timeout). At most one unresolved DNS/connect daemon globally. */
    private static final class Connector implements Runnable {
        String address; int port; volatile boolean done,cancelled; Socket socket; IOException error;
        Connector(String host,int number) { address=host;port=number; }
        public void run() {
            Socket opened=null;
            IOException failed=null;
            try { opened=new Socket(address,port); }
            catch(IOException ex) { failed=ex; }
            catch(RuntimeException ex) { failed=new IOException(ex.toString()); }
            synchronized(CONNECT_LOCK) {
                if(cancelled && opened!=null) { try { opened.close(); } catch(IOException ex) {} opened=null; }
                socket=opened;error=failed;done=true;
            }
        }
    }
    private static final class Packet {
        int type;byte[] body;
        Packet(int kind,byte[] data) { type=kind;body=new byte[data.length];System.arraycopy(data,0,body,0,data.length); }
    }
    private static final class Session implements Runnable {
        String address,nick,version;int port;
        volatile boolean running=true,connected,started;
        boolean host;int roomId,matchId,hostTeam,guestTeam=1,resultMatchId,resultStatus;
        int pauseMatchId;long pauseDeadline,lastPauseRequest;
        PlayerStats[] leaderboard;PlayerStats selfStats;
        boolean leaderboardPending,selfStatsPending;
        long lastLeaderboardRequest,lastSelfStatsRequest;
        Vector events=new Vector(),outgoing=new Vector(),inputs=new Vector();
        byte[] snapshot;Packet outgoingSnapshot;int outgoingBytes;
        Socket socket;volatile boolean link;volatile long writingSince;volatile int connectionSerial;
        Session(String server,int number,String name,String build) { address=server;port=number;nick=name;version=build; }
        void emit(Event event) {
            synchronized(CXOnlineTransport.class) {
                if(current!=this) return;
                if(event.type==ROOMS || event.type==LOBBY || event.type==CONNECTING || event.type==ERROR
                    || event.type==LEADERBOARD || event.type==SELF_STATS || event.type==RESULT || event.type==PAUSE)
                    for(int i=events.size()-1;i>=0;i--) if(((Event)events.elementAt(i)).type==event.type) events.removeElementAt(i);
                if(events.size()>=MAX_QUEUE) { events.removeAllElements();running=false;event=new Event(ERROR,"Event queue overflow; connection stopped"); }
                events.addElement(event);
            }
        }
        void resetRoom() {
            synchronized(CXOnlineTransport.class) {
                roomId=matchId=0;host=false;started=false;hostTeam=0;guestTeam=1;
                clearPause();
                snapshot=null;inputs.removeAllElements();outgoingSnapshot=null;
                outgoing.removeAllElements();outgoingBytes=0;
            }
        }
        void clearPause() { pauseMatchId=0;pauseDeadline=lastPauseRequest=0; }
        int pauseRemaining() {
            if(!connected || !started || pauseMatchId!=matchId || pauseDeadline==0) return 0;
            long remaining=pauseDeadline-System.currentTimeMillis();
            if(remaining<=0) return 0;
            return (int)Math.min(15000L,remaining);
        }
        boolean enqueue(int type,byte[] body) {
            synchronized(CXOnlineTransport.class) {
                if(!running || !connected || body==null || body.length>MAX_DATA) return false;
                if((type==W_SNAPSHOT || type==W_INPUT) && body.length==0) return false;
                if(type==W_SNAPSHOT) { outgoingSnapshot=new Packet(type,body);return true; }
                return enqueueOrdered(type,body);
            }
        }
        boolean enqueueOrdered(int type,byte[] body) {
            synchronized(CXOnlineTransport.class) {
                if(!running || !connected || body==null || body.length>MAX_DATA
                    || outgoing.size()>=MAX_QUEUE || outgoingBytes+body.length+5>MAX_BYTES) return false;
                outgoing.addElement(new Packet(type,body));outgoingBytes+=body.length+5;return true;
            }
        }
        void requestStats(boolean ranking) {
            synchronized(CXOnlineTransport.class) {
                if(!running || !connected) { emit(new Event(ERROR,"Not connected"));return; }
                if(ranking) leaderboardPending=true; else selfStatsPending=true;
            }
        }
        Packet nextPacket(int serial) {
            synchronized(CXOnlineTransport.class) {
                // A writer from an earlier connection must not consume this connection's queue.
                if(connectionSerial!=serial) return null;
                if(outgoing.size()>0) { Packet p=(Packet)outgoing.elementAt(0);outgoing.removeElementAt(0);outgoingBytes-=p.body.length+5;return p; }
                long now=System.currentTimeMillis();
                if(connected && leaderboardPending && (now<lastLeaderboardRequest || now-lastLeaderboardRequest>=300)) {
                    leaderboardPending=false;lastLeaderboardRequest=now;return new Packet(W_GET_LEADERBOARD,new byte[0]);
                }
                if(connected && selfStatsPending && (now<lastSelfStatsRequest || now-lastSelfStatsRequest>=300)) {
                    selfStatsPending=false;lastSelfStatsRequest=now;return new Packet(W_GET_SELF_STATS,new byte[0]);
                }
                Packet p=outgoingSnapshot;outgoingSnapshot=null;return p;
            }
        }
        Socket connect() throws IOException {
            Connector attempt=null;
            long begin=System.currentTimeMillis();
            while(running && current==this && attempt==null) {
                synchronized(CONNECT_LOCK) {
                    if(pendingConnector==null || pendingConnector.done) {
                        attempt=new Connector(address,port);pendingConnector=attempt;
                        Thread thread=new Thread(attempt,"Online relay connect");thread.setDaemon(true);thread.start();
                    }
                }
                if(attempt==null) { if(System.currentTimeMillis()-begin>15000) throw new IOException("Previous OS connect is still pending");sleep(50); }
            }
            if(attempt==null) throw new IOException("Stopped");
            begin=System.currentTimeMillis();
            while(running && current==this && !attempt.done && System.currentTimeMillis()-begin<15000) sleep(25);
            synchronized(CONNECT_LOCK) {
                if(!running || current!=this || !attempt.done) {
                    attempt.cancelled=true;
                    if(attempt.socket!=null) try { attempt.socket.close(); } catch(IOException ex) {}
                    throw new IOException("Connect timed out or stopped");
                }
                if(attempt.error!=null) throw attempt.error;
                return attempt.socket;
            }
        }
        public void run() {
            long retry=1000;
            while(running && current==this) {
                emit(new Event(CONNECTING,"Connecting to "+address+":"+port));
                try {
                    socket=connect();socket.setSoTimeout(1000);socket.setTcpNoDelay(true);writingSince=0;
                    link=true;
                    final OutputStream output=socket.getOutputStream();
                    final Socket connection=socket;
                    final int serial;
                    synchronized(CXOnlineTransport.class) { serial=++connectionSerial; }
                    Thread writer=new Thread(new Runnable(){public void run(){writeLoop(output,connection,serial);}},"Online relay writer");writer.setDaemon(true);writer.start();
                    ByteArrayOutputStream helloBytes=new ByteArrayOutputStream();
                    DataOutputStream hello=new DataOutputStream(helloBytes);
                    hello.writeShort(1);hello.write(textBytes(nick));hello.write(textBytes(version));hello.flush();
                    synchronized(CXOnlineTransport.class) { outgoing.addElement(new Packet(W_HELLO,helloBytes.toByteArray()));outgoingBytes+=helloBytes.size()+5; }
                    readLoop(socket.getInputStream());
                    retry=1000;
                } catch(IOException ex) { if(running && current==this) emit(new Event(DISCONNECTED,ex.toString())); }
                catch(RuntimeException ex) { if(running && current==this) emit(new Event(ERROR,ex.toString())); }
                finally {
                    link=false;connected=false;
                    synchronized(CXOnlineTransport.class) {
                        connectionSerial++;leaderboard=null;selfStats=null;resultMatchId=resultStatus=0;
                        leaderboardPending=selfStatsPending=false;lastLeaderboardRequest=lastSelfStatsRequest=0;
                    }
                    if(socket!=null) try { socket.close(); } catch(IOException ex) {}
                    socket=null;resetRoom();
                }
                long until=System.currentTimeMillis()+retry;
                while(running && current==this && System.currentTimeMillis()<until) sleep(50);
                retry=Math.min(10000,retry*2);
            }
        }
        void writeLoop(OutputStream stream,Socket connection,int serial) {
            DataOutputStream out=new DataOutputStream(stream);
            try {
                while(running && current==this && link && connectionSerial==serial) {
                    Packet packet=nextPacket(serial);
                    if(packet==null) { sleep(10);continue; }
                    if(connectionSerial!=serial) return;
                    writingSince=System.currentTimeMillis();
                    out.writeInt(packet.body.length+1);out.writeByte(packet.type);out.write(packet.body);out.flush();
                    synchronized(CXOnlineTransport.class) {
                        if(connectionSerial==serial) {
                            writingSince=0;
                            if(packet.type==W_GET_LEADERBOARD) lastLeaderboardRequest=System.currentTimeMillis();
                            if(packet.type==W_GET_SELF_STATS) lastSelfStatsRequest=System.currentTimeMillis();
                        }
                    }
                }
            } catch(IOException ex) { if(connectionSerial==serial) link=false;try { connection.close(); } catch(IOException ignored) {} }
            finally { if(connectionSerial==serial) writingSince=0; }
        }
        void readLoop(InputStream stream) throws IOException {
            long lastRead=System.currentTimeMillis(),lastPing=lastRead;
            long helloDeadline=lastRead+5000;
            // Preserve partial headers/payloads across SO_TIMEOUT (DataInputStream.readFully does not).
            byte[] header=new byte[4],body=null;int headerPos=0,bodyPos=0;
            while(running && current==this && link) {
                try {
                    if(body==null) {
                        int got=stream.read(header,headerPos,4-headerPos);
                        if(got<0) throw new IOException("Broker closed connection");
                        headerPos+=got;
                        if(headerPos==4) {
                            long length=((header[0]&255L)<<24)|((header[1]&255L)<<16)|((header[2]&255L)<<8)|(header[3]&255L);
                            if(length<1 || length>MAX_FRAME) throw new IOException("Frame size limit");
                            body=new byte[(int)length];bodyPos=0;
                        }
                    } else {
                        int got=stream.read(body,bodyPos,body.length-bodyPos);
                        if(got<0) throw new IOException("Broker closed connection");
                        bodyPos+=got;
                        if(bodyPos==body.length) { handle(body);body=null;headerPos=0;lastRead=System.currentTimeMillis(); }
                    }
                } catch(java.io.InterruptedIOException timeout) {}
                long now=System.currentTimeMillis();
                if(!connected && now>helloDeadline) throw new IOException("Broker handshake timeout");
                if(now-lastRead>45000) throw new IOException("Broker read timeout");
                if(writingSince!=0 && now-writingSince>5000) throw new IOException("Broker write timeout");
                if(connected && now-lastPing>10000) { enqueue(W_PING,new byte[0]);lastPing=now; }
            }
            throw new IOException("Connection ended");
        }
        void handle(byte[] body) throws IOException {
            DataInputStream in=new DataInputStream(new ByteArrayInputStream(body));int type=in.readUnsignedByte();
            if(type!=W_WELCOME && !connected) throw new IOException("Expected broker welcome");
            if(type==W_WELCOME) {
                in.readInt();connected=true;emit(new Event(CONNECTED,"Connected"));
            } else if(type==W_ROOMS) {
                int count=in.readUnsignedShort();if(count>128) throw new IOException("Room count limit");
                Event event=new Event(ROOMS,"Rooms");event.rooms=new Room[count];
                for(int i=0;i<count;i++) event.rooms[i]=readRoom(in);emit(event);
            } else if(type==W_LOBBY) {
                Room room=readRoom(in);boolean owner=in.readBoolean();
                if(room.id<=0 || !version.equals(room.version)) throw new IOException("Incompatible lobby version");
                Event event=new Event(LOBBY,"Lobby updated");event.roomId=room.id;event.roomName=room.name;event.version=room.version;
                event.hostNick=room.hostNick;event.guestNick=room.guestNick;event.hostReady=room.hostReady;event.guestReady=room.guestReady;
                event.hostTeam=room.hostTeam;event.guestTeam=room.guestTeam;event.matchId=room.matchId;event.isHost=owner;event.started=room.started;
                synchronized(CXOnlineTransport.class) {
                    roomId=room.id;host=owner;hostTeam=room.hostTeam;guestTeam=room.guestTeam;
                    // START is the only transition into a match; lobby may cancel a disconnected match.
                    if(!room.started) { started=false;matchId=0;clearPause();snapshot=null;inputs.removeAllElements();outgoingSnapshot=null; }
                }
                emit(event);
            } else if(type==W_START) {
                Event event=new Event(START,"Match started");event.version=version;event.matchId=in.readInt();event.hostTeam=in.readInt();event.guestTeam=in.readInt();event.isHost=in.readBoolean();event.started=true;
                if(!validTeam(event.hostTeam) || !validTeam(event.guestTeam) || event.matchId<=0) throw new IOException("Invalid match start");
                synchronized(CXOnlineTransport.class) {
                    if(roomId==0) throw new IOException("START outside lobby");
                    matchId=event.matchId;hostTeam=event.hostTeam;guestTeam=event.guestTeam;host=event.isHost;started=true;snapshot=null;inputs.removeAllElements();resultMatchId=matchId;resultStatus=0;
                    clearPause();
                    event.roomId=roomId;
                }
                emit(event);
            } else if(type==W_LEFT) { String message=in.available()>0?readText(in):"Left room";resetRoom();emit(new Event(LEFT,message)); }
            else if(type==W_LEADERBOARD) {
                int count=in.readUnsignedShort();if(count>50) throw new IOException("Leaderboard count limit");
                PlayerStats[] values=new PlayerStats[count];
                for(int i=0;i<count;i++) { values[i]=readStats(in);if(values[i].rank!=i+1 || values[i].games==0) throw new IOException("Invalid leaderboard rank"); }
                synchronized(CXOnlineTransport.class) { leaderboard=values; }
                Event event=new Event(LEADERBOARD,"Ranking updated");event.leaderboard=copyStats(values);emit(event);
            } else if(type==W_SELF_STATS) {
                PlayerStats value=readStats(in);
                synchronized(CXOnlineTransport.class) { selfStats=value; }
                Event event=new Event(SELF_STATS,"Player statistics updated");event.playerStats=copyStats(value);emit(event);
            } else if(type==W_RESULT_STATUS) {
                int id=in.readInt(),status=in.readInt();
                if(id<=0 || status<1 || status>3) throw new IOException("Invalid result status");
                synchronized(CXOnlineTransport.class) {
                    if(resultMatchId!=id) throw new IOException("Result status for another match");
                    resultStatus=status;
                }
                Event event=new Event(RESULT,"Match result updated");event.matchId=id;event.resultStatus=status;emit(event);
            } else if(type==W_PAUSE_STATE) {
                int id=in.readInt(),pausedByte=in.readUnsignedByte(),remaining=in.readInt();
                if(id<=0 || pausedByte>1 || remaining<0 || remaining>15000
                    || (pausedByte==0 && remaining!=0) || (pausedByte==1 && remaining==0))
                    throw new IOException("Invalid pause state");
                synchronized(CXOnlineTransport.class) {
                    if(!started || id!=matchId) throw new IOException("Pause state for another match");
                    pauseMatchId=id;pauseDeadline=pausedByte==1?System.currentTimeMillis()+remaining:0;
                    lastPauseRequest=0;
                    if(pausedByte==1) {
                        snapshot=null;inputs.removeAllElements();
                        // Discard unsent gameplay only, preserving all control,
                        // ping, terminal state and result acknowledgement order.
                        for(int i=outgoing.size()-1;i>=0;i--) {
                            Packet packet=(Packet)outgoing.elementAt(i);
                            if(packet.type==W_INPUT) { outgoingBytes-=packet.body.length+5;outgoing.removeElementAt(i); }
                        }
                    }
                }
                Event event=new Event(PAUSE,pausedByte==1?"Match paused":"Match resumed");
                event.matchId=id;event.paused=pausedByte==1;event.remainingMillis=remaining;emit(event);
            }
            else if(type==W_ERROR) emit(new Event(ERROR,readText(in)));
            else if(type==W_PONG) {}
            else if(type==W_SNAPSHOT || type==W_INPUT) {
                int size=in.available();if(size<1 || size>MAX_DATA) throw new IOException("Payload size limit");
                byte[] data=new byte[size];in.readFully(data);
                synchronized(CXOnlineTransport.class) {
                    if(!started || (type==W_SNAPSHOT && host) || (type==W_INPUT && !host)) throw new IOException("Unexpected relay direction");
                    if(type==W_SNAPSHOT) snapshot=data;
                    else { if(inputs.size()>=MAX_QUEUE) throw new IOException("Input queue overflow");inputs.addElement(data); }
                }
            } else throw new IOException("Unknown broker message");
            if(in.available()!=0) throw new IOException("Trailing frame bytes");
        }
    }
}
