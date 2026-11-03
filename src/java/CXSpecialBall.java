/** Preserve the asynchronous kick handoff when its taker reference is cleared. */
public final class CXSpecialBall {
    private CXSpecialBall() {}

    public static boolean BeforeUpdate(AIMatch match) {
        if (match == null) return false;
        if (!match.m_bSpecialBallStarted) return true;
        int state = AIMatch.GetMatchState();
        if (state < 4 || state > 7) return false;
        // PassSpecialBall clears this pointer before the AI kick event runs.
        // Skipping only this routine lets AIMatch.Update reach AITeam.Update.
        if (match.m_cSpecialFB == null) return false;
        if (state == 7 && match.m_cSpecialDestFB == null) return false;
        // These native scene objects can temporarily be absent during teardown.
        if (GameField.m_cBall == null) return false;
        if (state == 7 ? GameField.cCenter == null : match.m_cStrategy == null)
            return false;
        return true;
    }
}
