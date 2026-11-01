/** Scope the known native console-format exception without hiding unrelated failures. */
public final class CXLog {
    public static void SafeLog(String message) {
        try { GameObject.LogLine(message); }
        catch (IndexOutOfBoundsException knownConsoleBug) { GameObject.CrashLog(message); }
    }
}
