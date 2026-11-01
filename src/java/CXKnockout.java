/** Session-only knockout state. Never reports into a saved career tournament. */
public final class CXKnockout {
    static java.util.Vector teams;
    static MatchData[] games;
    static int[] winners;
    static boolean[] applied;
    static int next;
    static MatchData pending;
    static boolean completed;
    static boolean armed;

    public static String SetupTitle(MenuMultiplayer setup) {
        return setup instanceof CXKnockoutSetup ? "TURNIEJ" : Text.Get("&MenuTitleMultiplayer&");
    }

    public static void SetupInit(MenuMultiplayer setup) {
        UIWindow button = setup.GetElem("ID_CX_TOURNAMENT");
        if (button != null) setup.AddToSlideIn(button);
    }

    public static boolean HandleSetup(MenuMultiplayer source, UIWindow control, int command) {
        if (command != 0 || control == null || !"ID_CX_TOURNAMENT".equals(control.m_sId))
            return false;
        Leave();
        CoreLogic.m_bMultiplayer = true;
        CoreLogic.m_bChampionships = false;
        CoreLogic.m_bDemo = false;
        SoccerMainMenuModule module = (SoccerMainMenuModule)source.m_module;
        module.GetUI(18).Reset();
        module.ShowUI(18);
        return true;
    }

    public static boolean LoadUI(SoccerMainMenuModule module, int id) {
        if (id != 18 && id != 19) return false;
        SoccerUserInterface ui = (SoccerUserInterface)module.CreateObject(
            id == 18 ? "CXKnockoutSetup" : "CXKnockoutMenu");
        if (ui == null) throw new IllegalStateException("Unable to create tournament UI");
        Vector cursor = null;
        int current = SoccerMainMenuModule.m_nCurUI;
        if (current >= 0 && current < module.m_tUIs.length && module.m_tUIs[current] != null)
            cursor = module.m_tUIs[current].GetCursorPos();
        if (cursor == null) cursor = new Vector(GameObject.GetScreenWidth() / 2.0f,
            GameObject.GetScreenHeight() / 2.0f, 0.0f);
        ui.SetInitialCursorPos(cursor);
        if (!ui.Load(module, SoccerGame.GetResolution()))
            throw new IllegalStateException("Unable to load tournament UI");
        module.m_tUIs[id] = ui;
        ui.MoveTop();
        return true;
    }

    public static void Seed(CXKnockoutSetup setup) { CXGMWProfile.Seed(setup); }

    public static void Begin(CXKnockoutSetup setup) {
        if (setup.m_vPlayers.size() != 8) return;
        java.util.Vector chosen = new java.util.Vector();
        for (int i = 0; i < 8; i++) {
            MenuMultiplayer.MpTeamRecord record = (MenuMultiplayer.MpTeamRecord)setup.m_vPlayers.elementAt(i);
            if (record == null || record.GetTeamData() == null) return;
            chosen.addElement(record);
        }
        teams = chosen;
        games = new MatchData[7];
        winners = new int[7];
        applied = new boolean[7];
        for (int i = 0; i < 7; i++) winners[i] = -1;
        for (int i = 0; i < 4; i++) games[i] = new MatchData(i * 2, i * 2 + 1);
        next = 0;
        pending = null;
        completed = false;
        armed = true;
        CoreLogic.m_bMultiplayer = true;
        CoreLogic.m_bChampionships = false;
        CoreLogic.m_bDemo = false;
        ((SoccerMainMenuModule)setup.m_module).ShowUI(19);
    }

    static TeamData Team(int index) {
        return ((MenuMultiplayer.MpTeamRecord)teams.elementAt(index)).GetTeamData();
    }

    public static boolean IsFixture() {
        return armed && pending != null && Match.m_cMatchData == pending
            && CoreLogic.m_bMultiplayer && !CoreLogic.m_bChampionships;
    }

    public static boolean AllowGoldenGoal() {
        return IsFixture() || (CoreLogic.m_bChampionships
            && CoreLogic.GetPlayer().m_cChampionships.m_nPhase > 0);
    }

    public static int ReturnUI() { return armed && pending != null ? 19 : 17; }

    public static void FixReturnUI() {
        if (ReturnUI() == 19) SoccerMainMenuModule.m_nPrevUI = 19;
    }

    public static boolean PreMatchBack(MenuPreMatch menu) {
        if (ReturnUI() != 19) return false;
        if (!menu.bCheated && Match.m_cMatchData == pending) {
            pending.ResetResults();
            Match.m_cMatchData = null;
        }
        menu.bCheated = false;
        ((SoccerMainMenuModule)menu.m_module).ShowUI(19);
        return true;
    }

    public static void Completed() {
        if (IsFixture() && pending.GetWinner() >= 0) completed = true;
    }

    public static void Consume() {
        if (pending == null) return;
        MatchData result = pending;
        if (armed && completed && Match.m_cMatchData == result && games != null
            && next < 7 && games[next] == result && !applied[next] && result.GetWinner() >= 0) {
            winners[next] = result.GetWinner();
            applied[next] = true;
            next++;
            if (next == 4) {
                games[4] = new MatchData(winners[0], winners[1]);
                games[5] = new MatchData(winners[2], winners[3]);
            } else if (next == 6) games[6] = new MatchData(winners[4], winners[5]);
        } else result.ResetResults();
        if (Match.m_cMatchData == result) Match.m_cMatchData = null;
        pending = null;
        completed = false;
    }

    public static void Play(CXKnockoutMenu menu) {
        if (!armed || games == null) return;
        if (next >= 7) { Back(menu); return; }
        if (pending != null || applied[next] || games[next] == null) return;
        MatchData match = games[next];
        TeamData host = Team(match.m_nTeamHost);
        TeamData guest = Team(match.m_nTeamGuest);
        match.ResetResults();
        pending = match;
        completed = false;
        Match.m_cMatchData = match;
        CoreLogic.m_bMultiplayer = true;
        CoreLogic.m_bChampionships = false;
        CoreLogic.m_bDemo = false;
        CoreLogic.m_cTeamDataLeft = host;
        CoreLogic.m_cTeamDataRight = guest;
        CoreLogic.m_nNextLevel = ETeams.GetHomeField(host.m_nAnimalType);
        ((SoccerMainMenuModule)menu.m_module).ShowUI(9);
    }

    public static void Leave() {
        if (pending != null && Match.m_cMatchData == pending) Match.m_cMatchData = null;
        pending = null;
        completed = false;
        armed = false;
    }

    public static void Back(CXKnockoutMenu menu) {
        Leave();
        ((SoccerMainMenuModule)menu.m_module).ShowUI(18);
    }

    public static String Title() {
        return "TURNIEJ";
    }

    static String Label(int entrant, TeamData data) {
        String label = ((MenuMultiplayer.MpTeamRecord)teams.elementAt(entrant)).m_sPlayerName;
        if (label == null || label.length() == 0 || label.equals(data.m_sName)) label = data.m_sNameAbr;
        if (label.length() > 14) label = label.substring(0, 13) + "…";
        return label;
    }

    static String Fit(UIStatic widget, String text, String suffix) {
        float width = widget.GetSize().fX - 4.0f;
        if (width <= 4.0f) return text + suffix;
        Vector extent = widget.GetTextExtent(text + suffix);
        if (extent == null || extent.fX <= width) return text + suffix;
        while (text.length() > 1) {
            text = text.substring(0, text.length() - 1);
            String shortened = text + "…" + suffix;
            extent = widget.GetTextExtent(shortened);
            if (extent == null || extent.fX <= width) return shortened;
        }
        return text + "…" + suffix;
    }

    static void Entry(CXKnockoutMenu menu, String id, int entrant, int game, int side) {
        UIWindow root = menu.GetElem(id);
        UIWindowBlinking logo = (UIWindowBlinking)root.GetElem("ID_LOGO");
        UIStatic name = (UIStatic)root.GetElem("ID_NAME");
        UIWindow lost = root.GetElem("ID_LOST");
        lost.Hide();
        logo.EndBlink();
        if (entrant < 0) {
            logo.SetTexture(null);
            name.SetText("?");
        } else {
            TeamData data = Team(entrant);
            logo.SetTexture(data.m_cLogo);
            String label = Label(entrant, data);
            String suffix = "";
            if (applied[game]) {
                suffix = " " + (side == 0 ? games[game].m_nGoalsHost : games[game].m_nGoalsGuest);
                if (winners[game] != entrant) lost.Show();
            }
            name.SetText(Fit(name, label, suffix));
            if (game == next && next < 7 && games[next] != null &&
                (games[next].m_nTeamHost == entrant || games[next].m_nTeamGuest == entrant)) logo.Blink();
        }
        name.OnDisplayText();
    }

    public static void Render(CXKnockoutMenu menu) {
        menu.DisableCallMethod("HideChampion");
        menu.GetElem("ID_INFO_SCREEN").Hide();
        if (teams == null || games == null) return;
        for (int i = 0; i < 8; i++) Entry(menu, "ID_QFINAL_" + (i + 1), i, i / 2, i % 2);
        for (int i = 0; i < 4; i++) Entry(menu, "ID_SEMIFINAL_" + (i + 1), winners[i], 4 + i / 2, i % 2);
        for (int i = 0; i < 2; i++) Entry(menu, "ID_FINAL_" + (i + 1), winners[4 + i], 6, i);
        UIStatic button = (UIStatic)menu.GetElem("ID_OK");
        button.SetText(next >= 7 ? "NOWY" : "GRAJ");
        button.OnDisplayText();
        if (next >= 7) {
            UIStatic info = (UIStatic)menu.GetElem("ID_INFO_SCREEN_TEXT");
            info.SetText("MISTRZ\n" + Fit(info, Label(winners[6], Team(winners[6])), ""));
            info.OnDisplayText();
            menu.GetElem("ID_INFO_SCREEN").Show();
            menu.CallMethodIn("HideChampion", 3.0f);
        }
    }
}
