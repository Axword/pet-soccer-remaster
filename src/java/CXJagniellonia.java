/** One stock-style animal club. Definitions only at58; no save or cross-team edits. */
public final class CXJagniellonia {
    public static final int TEAM=58, HOME=42;
    private static final String LOGO="data/menu/logos/cx_jagniellonia.png";
    private static final String SILENCE="data/sounds/crossover/silence.wav";
    private static final String[] NAMES={"Slawomir Bramowicz","Bartek Welnowik","Taras Baranczuk","Jesus Imaaaz","Afimico Puchulu","Tomasz Franekowski","Bernardo Welnital"};
    private CXJagniellonia() {}

    /** Clone only named, audited per-species tables; global tables are excluded. */
    private static void CopyRow(Class owner,String[] names,int target,int source) {
        try {
            for(int i=0;i<names.length;i++) {
                java.lang.reflect.Field field=owner.getDeclaredField(names[i]);
                field.setAccessible(true);Object table=field.get(null);
                if(table==null || !field.getType().isArray() || java.lang.reflect.Array.getLength(table)<=target)
                    throw new IllegalStateException("Missing per-species table "+names[i]);
                java.lang.reflect.Array.set(table,target,java.lang.reflect.Array.get(table,source));
            }
        } catch(Exception failure) {throw new IllegalStateException("Jagniellonia definitions: "+failure);}
    }

    public static void Animals() {
        CopyRow(EAnimals.class,new String[]{"m_sMeshName","m_sTextureNormal","m_sTextureNormalLogo","m_sTexturePublic",
            "m_sTextureGoalKeeper","m_sTextureReferee","m_sScrFiles","m_sScrFilesGK","m_sNames","m_sNamesGK",
            "m_sTeamNamesWav","m_sTeamCommentsWav","m_sTeamCommentsWav_pol","m_sFBNamesWav","m_sFBNamesWav_pol",
            "m_sTeamMissWav","CXPlayers"},TEAM,0);
        EAnimals.m_sMeshName[TEAM]="cx_jagniaki_0.3da";
        EAnimals.m_sNames[TEAM]="Jagniaki";
        EAnimals.m_sNamesGK[TEAM]="Jagniaki";
        String[] kits=new String[5],gk=new String[5],logos=new String[5];
        for(int i=0;i<5;i++) {
            kits[i]="data/textures/tshirts/cx_jagniaki_0"+(i+1)+".png";
            gk[i]="data/textures/tshirts/cx_jagniaki_0"+((i+3)%5+1)+".png";
            logos[i]="data/menu/tshirtsicons/cx_jagniaki0"+(i+1)+".png";
        }
        EAnimals.m_sTextureNormal[TEAM]=kits;
        EAnimals.m_sTextureGoalKeeper[TEAM]=gk;
        EAnimals.m_sTextureNormalLogo[TEAM]=logos;
        EAnimals.m_sTexturePublic[TEAM]=kits[0];
        EAnimals.m_sTextureReferee[TEAM]=kits[0];
        EAnimals.CXPlayers[TEAM]=NAMES;
        EAnimals.m_sTeamNamesWav[TEAM]=SILENCE;
        EAnimals.m_sTeamCommentsWav[TEAM]=SILENCE;
        EAnimals.m_sTeamCommentsWav_pol[TEAM]=SILENCE;
        EAnimals.m_sTeamMissWav[TEAM]=SILENCE;
        String[][] player=(String[][])CXGMWProfile.Table(EAnimals.class,"m_sFBNamesWav");
        player[TEAM]=new String[]{SILENCE,SILENCE,SILENCE,SILENCE,SILENCE,SILENCE,SILENCE};
        EAnimals.m_sFBNamesWav_pol[TEAM]=new String[][]{{SILENCE,SILENCE},{SILENCE,SILENCE},{SILENCE,SILENCE},
            {SILENCE,SILENCE},{SILENCE,SILENCE},{SILENCE,SILENCE},{SILENCE,SILENCE}};
        // The old politician58 name/comment is never used. Generic match/Gothic
        // events remain unchanged; no new player-name dubbing is claimed.
    }

    public static void Teams() {
        CopyRow(ETeams.class,new String[]{"m_nSkillsStrength","m_nSkillsAccuracy","m_nSkillsTurning"},TEAM,0);
        TeamData[] table=(TeamData[])CXGMWProfile.Table(ETeams.class,"tTeams");
        table[TEAM]=new TeamData("Jagniellonia Bialystok","JAG","Jagniellonia",
            "Z podlaskich pastwisk prosto na boisko. Jagniellonia gra miekka welna i twarda noga. Jej napastnicy strzyga obrone, a bramkarz pilnuje, zeby pilka nie poszla w dluga.",
            "1. Slawomir Bramowicz\n2. Bartek Welnowik\n3. Taras Baranczuk\n4. Jesus Imaaaz\n5. Afimico Puchulu\n6. Tomasz Franekowski\n7. Bernardo Welnital",
            new UITexture(LOGO,256,256,0,0,256,256),TEAM);
    }

    public static void Maps() {
        CoreLogic.sLevelFileNames[HOME]="data/levels/podlasie/podlasie.map";
        CoreLogic.sLevelNames[HOME]="Podlaska Polana";
        CoreLogic.sLevelMusic[HOME]=CoreLogic.sLevelMusic[2];
        CoreLogic.sLevelLoopSounds[HOME]=CoreLogic.sLevelLoopSounds[2];
    }

    public static void load(MeshObject object,int animal) {
        if(animal!=TEAM) {CXAnimalIdentity.load(object,animal);return;}
        // Prime original MIS0 physics even when this club is loaded first and
        // no original bear has appeared yet. No actor is held in that cache.
        CXAnimalIdentity.ensureBase(object,0);
        int slot=object instanceof FootBaller?((FootBaller)object).m_nNumberInTeam:0;
        if(slot<0 || slot>6)slot=0;
        object.LoadMesh("data/meshes/animals/cx_jagniaki_"+slot+".3da");
    }
}
