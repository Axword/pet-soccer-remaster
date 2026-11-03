/** Add one closed LoL club to the existing GMW profile; no gameplay changes. */
public final class CXLoLProfile {
    private static final String[] names={"Warwick","Nasus","Ahri","Garen","Jinx","Teemo","Blitzcrank"};
    private static final String[] stems={"cx_warwick","cx_nasus","cx_ahri","cx_garen","cx_jinx","cx_teemo","cx_blitzcrank"};
    private static final String silence="data/sounds/crossover/silence.wav";
    private static final String logo="data/menu/logos/cx_faction30.png";
    private CXLoLProfile() {}

    public static void Animals() {
        String[][] playerWaves=(String[][])CXGMWProfile.Table(EAnimals.class,"m_sFBNamesWav");
        for(int slot=0;slot<7;slot++) {
            int species=30+slot;
            String texture="data/textures/"+stems[slot]+".png";
            EAnimals.m_sMeshName[species]=stems[slot]+".3da";
            EAnimals.m_sTextureNormal[species]=new String[]{texture};
            EAnimals.m_sTextureGoalKeeper[species]=new String[]{texture};
            EAnimals.m_sTextureNormalLogo[species]=new String[]{logo};
            EAnimals.m_sTexturePublic[species]=EAnimals.m_sTexturePublic[11];
            EAnimals.m_sTextureReferee[species]=EAnimals.m_sTextureReferee[11];
            EAnimals.m_sScrFiles[species]=EAnimals.m_sScrFiles[11];
            EAnimals.m_sScrFilesGK[species]=EAnimals.m_sScrFilesGK[11];
            // Entity class names remain the existing robot adapters. Player
            // names are separately resolved by the installed mixed-squad code.
            EAnimals.m_sNames[species]=EAnimals.m_sNames[11];
            EAnimals.m_sNamesGK[species]=EAnimals.m_sNamesGK[11];
            EAnimals.CXPlayers[species]=new String[]{names[slot],names[slot],names[slot],names[slot],names[slot],names[slot],names[slot]};
            // No new-name recording is claimed. Generic commentary is kept;
            // silent name calls avoid speaking an unrelated stock player/club.
            EAnimals.m_sTeamNamesWav[species]=silence;
            EAnimals.m_sTeamCommentsWav[species]=silence;
            EAnimals.m_sTeamCommentsWav_pol[species]=silence;
            playerWaves[species]=new String[]{silence,silence,silence,silence,silence,silence,silence};
            EAnimals.m_sFBNamesWav_pol[species]=new String[][]{
                {silence,silence},{silence,silence},{silence,silence},{silence,silence},
                {silence,silence},{silence,silence},{silence,silence}};
            EAnimals.m_sTeamMissWav[species]=EAnimals.m_sTeamMissWav[11];
        }
    }
    public static void Teams() {
        TeamData[] table=(TeamData[])CXGMWProfile.Table(ETeams.class,"tTeams");
        TeamData team=new TeamData("Real Runeterra","RRT","Runeterra",
            "Klub mistrzow Runeterry. Nazwa nawiazuje do Realu Madryt.",
            "1. Warwick\n2. Nasus\n3. Ahri\n4. Garen\n5. Jinx\n6. Teemo\n7. Blitzcrank",
            new UITexture(logo,256,256,0,0,256,256),30);
        for(int species=30;species<=36;species++)table[species]=team;
    }
    public static void Maps() {
        CoreLogic.sLevelFileNames[39]="data/levels/summonerrift/summonerrift.map";
        CoreLogic.sLevelNames[39]="Summoner's Rift";
        CoreLogic.sLevelMusic[39]=CoreLogic.sLevelMusic[0];
        CoreLogic.sLevelLoopSounds[39]=CoreLogic.sLevelLoopSounds[0];
    }
}
