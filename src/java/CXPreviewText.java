/** Menu-local display text only. Canonical TeamData strings are never changed. */
public final class CXPreviewText {
    private CXPreviewText() {}

    public static String Name(TeamData team) {
        String name = team.m_sName;
        if ("G\u00f3rnik Khorinis".equals(name)) return "Gornik Khorinis";
        if ("Wied\u017aminhampton".equals(name)) return "Wiedzminhampton";
        return name;
    }

    public static String Description(TeamData team) {
        String name = team.m_sName;
        if ("Borussia Blockmund".equals(name)
                || "G\u00f3rnik Khorinis".equals(name)
                || "Wied\u017aminhampton".equals(name)) return "";
        return team.m_sInfo;
    }
}
