import java.io.*;

/** Owned bounded wire format; it never calls the game engine. */
public final class CXOnlineState {
    public static final int MAGIC = 0x43584f31;
    public static final int VERSION = 3;
    public static final int MAX_ACTORS = 34;
    public static final class Actor {
        public float[] transform = new float[9]; // position, forward, up
        public String animation = "";
        public int animationFlags, animationSerial;
    }
    public static final class Frame {
        public int matchId, sequence, state, half, leftScore, rightScore;
        public int hostIndex;
        public boolean selectionVisible;
        public int selectionTeam=-1;
        public float[] selectionPosition=new float[3];
        public int hudEvent=-1,hudSerial;
        public float clock;
        public int[] count = new int[2], side = new int[2], focus = new int[2], active = new int[2];
        public boolean playing, finished;
        public Actor[] actors;
    }
    private static boolean bounded(float x, float limit) {
        return x == x && x <= limit && x >= -limit;
    }
    public static boolean valid(Frame f) {
        if (f == null || f.matchId < 1 || f.sequence < 0 || f.state < 0 || f.state > 16
            || f.half < 0 || f.half > 4 || f.leftScore < 0 || f.leftScore > 999
            || f.rightScore < 0 || f.rightScore > 999 || !bounded(f.clock, 86400) || f.clock < 0
            || f.hudEvent < -1 || f.hudEvent > 2 || f.hudSerial < 0
            || f.hostIndex < 0 || f.hostIndex > 1 || f.selectionTeam < -1 || f.selectionTeam > 1
            || (f.selectionVisible && f.selectionTeam < 0) || f.selectionPosition==null || f.selectionPosition.length!=3
            || (f.finished && (f.state!=3 || f.half!=1 || f.clock<60))) return false;
        for(int i=0;i<3;i++)if(!bounded(f.selectionPosition[i],1000000))return false;
        int n = 2; // ball and referee, after both teams
        for (int t=0;t<2;t++) {
            if (f.count[t] < 1 || f.count[t] > 16 || f.side[t] < 0 || f.side[t] > 1
                || f.focus[t] < -1 || f.focus[t] >= f.count[t]
                || f.active[t] < -1 || f.active[t] >= f.count[t]) return false;
            n += f.count[t];
        }
        if (n > MAX_ACTORS || f.actors == null || f.actors.length != n) return false;
        for (int i=0;i<n;i++) {
            Actor a=f.actors[i];
            if (a==null || a.transform==null || a.transform.length!=9 || a.animation==null
                || a.animation.length()>80 || a.animationFlags < -1 || a.animationFlags > 65535) return false;
            for (int j=0;j<9;j++) if (!bounded(a.transform[j],j<3?1000000:1.1f)) return false;
            for (int j=0;j<a.animation.length();j++) if (a.animation.charAt(j)<32) return false;
            float fwd=a.transform[3]*a.transform[3]+a.transform[4]*a.transform[4]+a.transform[5]*a.transform[5];
            float up=a.transform[6]*a.transform[6]+a.transform[7]*a.transform[7]+a.transform[8]*a.transform[8];
            float dot=a.transform[3]*a.transform[6]+a.transform[4]*a.transform[7]+a.transform[5]*a.transform[8];
            if (fwd<0.1f || fwd>1.3f || up<0.1f || up>1.3f || dot>.2f || dot< -.2f) return false;
        }
        return true;
    }
    public static byte[] encode(Frame f) throws IOException {
        if (!valid(f)) throw new IOException("Invalid snapshot");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream(2048);
        DataOutputStream out=new DataOutputStream(bytes);
        out.writeInt(MAGIC); out.writeInt(VERSION); out.writeInt(f.matchId); out.writeInt(f.sequence);
        out.writeInt(f.state); out.writeInt(f.half); out.writeInt(f.leftScore); out.writeInt(f.rightScore);
        out.writeInt(f.hudEvent);out.writeInt(f.hudSerial);
        out.writeInt(f.hostIndex);
        out.writeBoolean(f.selectionVisible);out.writeInt(f.selectionTeam);
        for(int j=0;j<3;j++)out.writeFloat(f.selectionPosition[j]);
        out.writeFloat(f.clock); out.writeBoolean(f.playing);out.writeBoolean(f.finished);
        for (int t=0;t<2;t++) { out.writeInt(f.count[t]);out.writeInt(f.side[t]);out.writeInt(f.focus[t]);out.writeInt(f.active[t]); }
        out.writeInt(f.actors.length);
        for (int i=0;i<f.actors.length;i++) {
            Actor a=f.actors[i];
            for (int j=0;j<9;j++) out.writeFloat(a.transform[j]);
            out.writeUTF(a.animation);out.writeInt(a.animationFlags);out.writeInt(a.animationSerial);
        }
        out.flush();return bytes.toByteArray();
    }
    public static Frame decode(byte[] data) throws IOException {
        if (data==null || data.length<102 || data.length>32768) throw new IOException("Snapshot length");
        DataInputStream in=new DataInputStream(new ByteArrayInputStream(data));
        if (in.readInt()!=MAGIC || in.readInt()!=VERSION) throw new IOException("Snapshot version");
        Frame f=new Frame();f.matchId=in.readInt();f.sequence=in.readInt();f.state=in.readInt();
        f.half=in.readInt();f.leftScore=in.readInt();f.rightScore=in.readInt();
        f.hudEvent=in.readInt();f.hudSerial=in.readInt();f.hostIndex=in.readInt();
        f.selectionVisible=in.readBoolean();f.selectionTeam=in.readInt();
        for(int j=0;j<3;j++)f.selectionPosition[j]=in.readFloat();
        f.clock=in.readFloat();f.playing=in.readBoolean();f.finished=in.readBoolean();
        for (int t=0;t<2;t++) {f.count[t]=in.readInt();f.side[t]=in.readInt();f.focus[t]=in.readInt();f.active[t]=in.readInt();}
        int n=in.readInt();if(n<4 || n>MAX_ACTORS)throw new IOException("Actor count");
        f.actors=new Actor[n];
        for(int i=0;i<n;i++) {
            Actor a=new Actor();f.actors[i]=a;
            for(int j=0;j<9;j++)a.transform[j]=in.readFloat();
            a.animation=in.readUTF();a.animationFlags=in.readInt();a.animationSerial=in.readInt();
        }
        if (in.available()!=0 || !valid(f))throw new IOException("Snapshot data");
        return f;
    }
}
