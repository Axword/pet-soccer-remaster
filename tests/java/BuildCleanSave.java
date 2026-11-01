/** Uses unchanged game serializer classes to create a clean unlocked profile. */
public final class BuildCleanSave {
    static int checks;
    static void require(boolean condition, String detail) {
        checks++;
        if (!condition) throw new IllegalStateException(detail);
    }
    static void verifyPlayer(PlayerSave player) {
        require("Gracz".equals(player.m_Name), "clean display name");
        require(player.m_tTeamsAvailable.length == 12, "historical twelve-team save layout");
        for (int i = 0; i < player.m_tTeamsAvailable.length; i++) {
            require(player.m_tTeamsAvailable[i], "original team flag " + i);
            require(player.IsTeamAvailable(i), "original team available " + i);
        }
        for (int i = 0; i < player.m_tExtrasAvailable.length; i++)
            require(player.m_tExtrasAvailable[i], "extra field flag " + i);
        int[] extraSpecies = {37, 44, 51};
        for (int i = 0; i < extraSpecies.length; i++)
            require(player.IsTeamAvailable(extraSpecies[i]), "custom team availability " + extraSpecies[i]);
        require(player.m_nMatchHalfTimeIndex == 1, "historical duration default");
        require(player.m_nDiffLevel == 7 && player.m_nDiffSetting == 1, "all difficulty levels unlocked; selected difficulty stays normal");
        require(player.GetHalfTime() == 240, "historical 4-minute half default");
        require(player.m_Kb0.m_Device == 0 && player.m_Kb1.m_Device == 0, "fresh keyboard profile defaults");
        require(player.m_Kb0.m_JoyNumber == 0 && player.m_Kb1.m_JoyNumber == 1, "distinct original default port slots");
        Championships c = player.m_cChampionships;
        require(c != null && c.m_nPhase == 0, "fresh career phase");
        require(c.m_nPlayerTeam == -1 && c.m_nPlayerTeamClothes == -1 && c.m_nPlayerGroup == -1, "no active career team");
        require(c.m_vAllTeams.size() == 0, "no career results");
        require(c.m_vGroupA.size() + c.m_vGroupB.size() + c.m_vGroupC.size() + c.m_vGroupD.size() == 0, "empty groups");
        require(c.m_cNextMatch == null && c.m_cFinal == null, "no pending fixture");
        require(c.m_bStartNextChampionships && !c.m_bIsReplayingMatch, "fresh career state");
        require(c.m_nCurChampionships == 0 && c.m_nPrevChampWinner == -1, "no personal championship progress");
    }
    static void write(GameSerializeSettings settings, String path) {
        Stream stream = new Stream(path);
        require(stream.OpenStream(0), "open output");
        require(settings.SaveSettings(stream), "serialize with actual game serializer");
        require(stream.Close(), "close output");
    }
    public static void main(String[] args) throws Exception {
        require(args.length == 2, "two output paths");
        GameSerializeSettings settings = new GameSerializeSettings();
        PlayerSave player = new PlayerSave();
        player.SetDefault();
        player.SetName("Gracz");
        player.m_nDiffLevel = 7;
        for (int i = 0; i < player.m_tTeamsAvailable.length; i++) player.m_tTeamsAvailable[i] = true;
        for (int i = 0; i < player.m_tExtrasAvailable.length; i++) player.m_tExtrasAvailable[i] = true;
        GameSerializeSettings.Logic.m_Players.removeAllElements();
        GameSerializeSettings.Logic.m_Players.addElement(player);
        CoreLogic.m_cCurPlayer = player;
        settings.m_nLastPlayerIndex = 0;
        settings.m_Resolution = 2;
        verifyPlayer(player);
        write(settings, args[0]);
        Stream input = new Stream(args[0]);
        require(input.OpenStream(1), "open clean profile");
        GameSerializeSettings read = new GameSerializeSettings();
        require(read.LoadSettings(input), "actual game loader accepts new profile");
        require(input.in.read() == -1, "no unparsed trailing data");
        require(input.Close(), "close input");
        require(GameSerializeSettings.Logic.m_Players.size() == 1, "one clean profile");
        PlayerSave restored = (PlayerSave)GameSerializeSettings.Logic.m_Players.elementAt(0);
        verifyPlayer(restored);
        require(read.m_nLastPlayerIndex == 0, "clean selected profile");
        require(read.m_Resolution == 1, "resolution is not serialized; fresh constructor default retained");
        write(read, args[1]);
        System.out.println("CLEAN_SAVE_PASS checks=" + checks + " name=Gracz original_unlocked=12 custom_available=3 extras=" + restored.m_tExtrasAvailable.length + " fresh_career=true");
    }
}
