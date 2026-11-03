import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.util.StringTokenizer;

/** Selection-only content preference. Never changes team definitions or player saves. */
public final class CXTeamVisibility {
    private static boolean enabled;
    private static java.util.WeakHashMap menus=new java.util.WeakHashMap();

    private CXTeamVisibility() {}

    public static boolean IsCrossover(int species) {
        return species==30 || species==37 || species==44 || species==51;
    }
    public static boolean IsAdditional(int species) {return IsCrossover(species)||species==58;}
    /** Pure cached read; safe for Online button/UI checks on every frame. */
    public static boolean Visible(int species) { return !IsAdditional(species) || enabled; }
    public static boolean Enabled() { return enabled; }

    /** Called on selector entry/button actions only, never from a frame/render hook. */
    public static void Reload() {
        boolean value=false;
        FileInputStream in=null;
        try {
            in=new FileInputStream("CXSupport.ini");
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            byte[] chunk=new byte[2048];
            int count,total=0;
            while((count=in.read(chunk))!=-1) {
                total+=count;
                if(total>65536)throw new java.io.IOException("Content preferences too large");
                bytes.write(chunk,0,count);
            }
            value=Parse(new String(bytes.toByteArray(),"ISO-8859-1"));
        } catch(Exception ignored) {
            // Missing/invalid preference keeps the original animal clubs visible.
        } finally {
            if(in!=null)try{in.close();}catch(java.io.IOException ignored){}
        }
        enabled=value;
    }

    static boolean Parse(String contents) {
        boolean content=false;
        StringTokenizer lines=new StringTokenizer(contents,"\r\n");
        while(lines.hasMoreTokens()) {
            String line=lines.nextToken().trim();
            if(line.length()==0 || line.charAt(0)==';' || line.charAt(0)=='#')continue;
            if(line.charAt(0)=='[') { content=line.equalsIgnoreCase("[Content]");continue; }
            if(!content)continue;
            int at=line.indexOf('=');
            if(at<0 || !line.substring(0,at).trim().equalsIgnoreCase("ExtraTeams"))continue;
            String setting=line.substring(at+1).trim();
            int comment=setting.indexOf(';');
            if(comment>=0)setting=setting.substring(0,comment).trim();
            return setting.equals("1");
        }
        return false;
    }

    /** First selector entry captures the full original OnCreate, including new animal clubs. */
    public static void Register(MenuChooseTeam menu) {
        TeamData[] allTeams=new TeamData[menu.tTeams.length];
        System.arraycopy(menu.tTeams,0,allTeams,0,allTeams.length);
        Object[] state={allTeams,enabled?Boolean.FALSE:Boolean.TRUE};
        menus.put(menu,state);
        Apply(menu,state);
    }

    public static void Refresh(MenuChooseTeam menu) {
        Reload();
        Object[] state=(Object[])menus.get(menu);
        if(state==null)Register(menu);
        else Apply(menu,state);
    }

    private static int SpeciesAt(TeamData[] teams,int index) {
        return teams!=null && index>=0 && index<teams.length && teams[index]!=null?teams[index].m_nAnimalType:-1;
    }
    private static int Find(TeamData[] teams,int species) {
        for(int i=0;i<teams.length;i++)if(teams[i].m_nAnimalType==species)return i;
        return 0;
    }
    private static void Apply(MenuChooseTeam menu,Object[] state) {
        TeamData[] allTeams=(TeamData[])state[0];
        if(((Boolean)state[1]).booleanValue()==enabled && menu.tTeams!=allTeams)return;
        int selected=SpeciesAt(menu.tTeams,menu.m_nChosen);
        int player1=SpeciesAt(menu.tTeams,menu.m_nChosenPlayer1);
        int count=0;
        for(int i=0;i<allTeams.length;i++)if(allTeams[i]!=null && Visible(allTeams[i].m_nAnimalType))count++;
        if(count==0)throw new IllegalStateException("No animal clubs in selection");
        TeamData[] visible=new TeamData[count];int next=0;
        for(int i=0;i<allTeams.length;i++)if(allTeams[i]!=null && Visible(allTeams[i].m_nAnimalType))visible[next++]=allTeams[i];
        menu.tTeams=visible;
        menu.m_nChosen=Find(visible,selected);
        menu.m_nChosenPlayer1=Find(visible,player1);
        state[1]=enabled?Boolean.TRUE:Boolean.FALSE;
    }

    /** Only an unsaved team-selection setup is normalized, not a league/save. */
    public static void PrepareMultiplayer(MenuMultiplayer menu) {
        if(!(menu.m_module instanceof SoccerMainMenuModule))return;
        SoccerMainMenuModule module=(SoccerMainMenuModule)menu.m_module;
        MenuChooseTeam source=(MenuChooseTeam)module.GetUI(2);
        if(source==null)return;
        Refresh(source);
        menu.m_tTeams=source.tTeams;
        if(menu.m_vPlayers==null)return;
        for(int i=0;i<menu.m_vPlayers.size();i++) {
            MenuMultiplayer.MpTeamRecord record=(MenuMultiplayer.MpTeamRecord)menu.m_vPlayers.elementAt(i);
            TeamData team=record.GetTeamData();
            if(team!=null && !Visible(team.m_nAnimalType))record.SetTeamData(source.tTeams[0]);
        }
        if(menu.m_nChosen<0 || menu.m_nChosen>=menu.m_tTeams.length)menu.m_nChosen=0;
    }

    public static boolean SupportsOnline(int species,int[] ids) {
        if(!Visible(species))return false;
        for(int i=0;i<ids.length;i++)if(ids[i]==species)return true;
        return false;
    }
    public static int NextOnline(int species,int delta,int[] ids) {
        Reload();
        if(ids==null || ids.length==0)return 0;
        int index=0;
        for(int i=0;i<ids.length;i++)if(ids[i]==species){index=i;break;}
        int step=delta<0?-1:1;
        for(int tries=0;tries<ids.length;tries++) {
            index=(index+step+ids.length)%ids.length;
            if(Visible(ids[index]))return ids[index];
        }
        return 0;
    }
}
