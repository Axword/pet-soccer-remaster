// Native-free test doubles only. Production CXKnockout.class and MatchData.class
// are copied byte-for-byte; none of these stubs enters a delivered game pack.
class GameObject {
    public static int GetScreenWidth() { return 1024; }
    public static int GetScreenHeight() { return 768; }
    public void DisableCallMethod(String name) {}
    public void CallMethodIn(String name, float delay) {}
}
class Module extends GameObject {}
class Vector { Vector(float x, float y, float z) {} }
class UITexture {}
class UIWindow extends GameObject {
    public String m_sId;
    public Module m_module;
    public UIWindow GetElem(String id) { return null; }
    public void Hide() {}
    public void Show() {}
}
class UIStatic extends UIWindow {
    public void SetText(String text) {}
    public void OnDisplayText() {}
}
class UIWindowBlinking extends UIWindow {
    public void EndBlink() {}
    public void SetTexture(UITexture value) {}
    public void Blink() {}
}
class SoccerUserInterface extends UIWindow {
    public void Reset() {}
    public Vector GetCursorPos() { return null; }
    public void SetInitialCursorPos(Vector pos) {}
    public boolean Load(Module module, int resolution) { return true; }
    public void MoveTop() {}
    public void AddToSlideIn(UIWindow window) {}
}
class SoccerMainMenuModule extends Module {
    static int m_nCurUI, m_nPrevUI;
    SoccerUserInterface[] m_tUIs = new SoccerUserInterface[20];
    int shown = -1;
    public SoccerUserInterface GetUI(int id) { return m_tUIs[id]; }
    public void ShowUI(int id) { shown = id; }
    public GameObject CreateObject(String name) { return null; }
}
class MenuMultiplayer extends SoccerUserInterface {
    java.util.Vector m_vPlayers = new java.util.Vector();
    public class MpTeamRecord {
        TeamData data;
        String m_sPlayerName;
        public MpTeamRecord(TeamData team, String name) { data=team; m_sPlayerName=name; }
        public TeamData GetTeamData() { return data; }
    }
}
class CXKnockoutSetup extends MenuMultiplayer {}
class CXKnockoutMenu extends SoccerUserInterface {}
class MenuChooseTeam extends SoccerUserInterface {
    TeamData[] available;
    public TeamData[] GetTeams() { return available; }
}
class MenuPreMatch extends SoccerUserInterface { boolean bCheated; }
class TeamData {
    String m_sName, m_sNameAbr;
    int m_nAnimalType;
    UITexture m_cLogo;
    TeamData(int id) { m_nAnimalType=id; m_sName="Team"+id; m_sNameAbr="T"+id; }
}
class ETeams { public static int GetHomeField(int species) { return 100+species; } }
class Championships { int m_nPhase; }
class PlayerSave { Championships m_cChampionships = new Championships(); }
class CoreLogic {
    static boolean m_bMultiplayer, m_bChampionships, m_bDemo;
    static int m_nNextLevel;
    static TeamData m_cTeamDataLeft, m_cTeamDataRight;
    static PlayerSave player = new PlayerSave();
    static int calls;
    public static PlayerSave GetPlayer() { calls++; return player; }
}
class SoccerGame { public static int GetResolution() { return 2; } }
class Match { static MatchData m_cMatchData; }
class Text { public static String Get(String key) { return key; } }
