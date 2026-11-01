/** Installer-only asset closure. Stable historical indices remain allocated. */
public final class CXGMWProfile {
    static Object Table(Class owner, String name) {
        try {
            java.lang.reflect.Field field=owner.getDeclaredField(name);
            field.setAccessible(true);
            return field.get(null);
        } catch(Exception failure) { throw new IllegalStateException("Profile table: "+name+": "+failure); }
    }
    public static boolean Selected(int species) {
        return species >= 0 && (species <= 12 || species >= 37 && species <= 57);
    }
    public static int Species(int species) {
        return species >= 13 && !Selected(species) ? 11 : species;
    }
    public static int Map(int level) {
        return level >= 21 && level != 38 && level != 40 && level != 41 ? 0 : level;
    }
    public static int SeedIndex(int slot, int available) {
        if (available == 15) return slot < 5 ? slot : slot + 7;
        return available >= 20 ? 12 + slot : slot % available;
    }
    public static void Seed(CXKnockoutSetup setup) {
        if (setup.m_vPlayers.size() != 0) return;
        SoccerMainMenuModule module = (SoccerMainMenuModule)setup.m_module;
        TeamData[] available = ((MenuChooseTeam)module.GetUI(2)).GetTeams();
        for (int i=0; i<8; i++) {
            TeamData team=available[SeedIndex(i,available.length)];
            setup.m_vPlayers.addElement(setup.new MpTeamRecord(team,team.m_sName));
        }
    }
    public static void Animals() {
        String[] names={"Robo","Robo","Robo","Robo","Robo","Robo","Robo"};
        String[][] playerWaves=(String[][])Table(EAnimals.class,"m_sFBNamesWav");
        for(int i=13;i<86;i++) if(!Selected(i)) {
            EAnimals.m_sMeshName[i]=EAnimals.m_sMeshName[11];
            EAnimals.m_sTextureNormal[i]=EAnimals.m_sTextureNormal[11];
            EAnimals.m_sTextureNormalLogo[i]=EAnimals.m_sTextureNormalLogo[11];
            EAnimals.m_sTexturePublic[i]=EAnimals.m_sTexturePublic[11];
            EAnimals.m_sTextureGoalKeeper[i]=EAnimals.m_sTextureGoalKeeper[11];
            EAnimals.m_sTextureReferee[i]=EAnimals.m_sTextureReferee[11];
            EAnimals.m_sScrFiles[i]=EAnimals.m_sScrFiles[11];
            EAnimals.m_sScrFilesGK[i]=EAnimals.m_sScrFilesGK[11];
            EAnimals.m_sNames[i]=EAnimals.m_sNames[11];
            EAnimals.m_sNamesGK[i]=EAnimals.m_sNamesGK[11];
            EAnimals.m_sTeamNamesWav[i]=EAnimals.m_sTeamNamesWav[11];
            EAnimals.m_sTeamCommentsWav[i]=EAnimals.m_sTeamCommentsWav[11];
            EAnimals.m_sTeamCommentsWav_pol[i]=EAnimals.m_sTeamCommentsWav_pol[11];
            playerWaves[i]=playerWaves[11];
            EAnimals.m_sFBNamesWav_pol[i]=EAnimals.m_sFBNamesWav_pol[11];
            EAnimals.m_sTeamMissWav[i]=EAnimals.m_sTeamMissWav[11];
            EAnimals.CXPlayers[i]=names;
        }
        for(int i=0;i<EAnimals.CXVoice.length;i++) EAnimals.CXVoice[i]=playerWaves[11][0];
    }
    public static void TeamStats() {
        int[] strength=(int[])Table(ETeams.class,"m_nSkillsStrength");
        int[] accuracy=(int[])Table(ETeams.class,"m_nSkillsAccuracy");
        int[] turning=(int[])Table(ETeams.class,"m_nSkillsTurning");
        for(int i=13;i<86;i++) if(!Selected(i)) {
            strength[i]=strength[11];
            accuracy[i]=accuracy[11];
            turning[i]=turning[11];
        }
        for(int i=0;i<ETeams.CXHomes.length;i++) ETeams.CXHomes[i]=0;
    }
    public static void Teams() {
        TeamData[] teams=(TeamData[])Table(ETeams.class,"tTeams");
        for(int i=13;i<86;i++) if(!Selected(i)) teams[i]=teams[11];
    }
    public static void Maps() {
        for(int i=21;i<CoreLogic.sLevelFileNames.length;i++) if(Map(i)!=i) {
            CoreLogic.sLevelFileNames[i]=CoreLogic.sLevelFileNames[0];
            CoreLogic.sLevelNames[i]=CoreLogic.sLevelNames[0];
            CoreLogic.sLevelMusic[i]=CoreLogic.sLevelMusic[0];
            CoreLogic.sLevelLoopSounds[i]=CoreLogic.sLevelLoopSounds[0];
        }
    }
}
