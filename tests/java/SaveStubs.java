/** Headless-only native boundaries. None of these classes are shipped. */
class GameObject {
    public GameObject() {}
    public static void CrashLog(String value) {}
    public static void LogLine(String value) {}
}
class SoccerGame extends GameObject {
    static boolean m_bDebug = false;
    static SoccerGame game;
    static GameSerializeSettings m_cSettings;
    public static void SaveAttrib() {}
}
class SoccerModule {
    static boolean m_bRenderPublic = true;
}
class CXLog {
    public static void SafeLog(String value) {}
}
class Text {
    public static String Get(String value) { return value; }
}
class Cheat {
    static boolean m_bAllTeams = false;
    static boolean m_bAllExtras = false;
}
