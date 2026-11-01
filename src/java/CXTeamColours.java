/** Wardrobe bounds and menu rebuilding for the three-club release profile. */
public final class CXTeamColours {
    private CXTeamColours() {}

    public static void Init() {
        for (int species=37; species<=57; species++) {
            String icon = species < 44 ? "data/menu/logos/cx_faction31.png"
                : species < 51 ? "data/menu/logos/cx_faction32.png"
                : "data/menu/logos/cx_faction33.png";
            EAnimals.m_sTextureNormal[species] =
                new String[] { EAnimals.m_sTextureNormal[species][0] };
            EAnimals.m_sTextureGoalKeeper[species] =
                new String[] { EAnimals.m_sTextureGoalKeeper[species][0] };
            EAnimals.m_sTextureNormalLogo[species] = new String[] { icon };
        }
    }

    public static int Count(int species) {
        int count = EAnimals.m_sTextureNormal[species].length;
        int keepers = EAnimals.m_sTextureGoalKeeper[species].length;
        int icons = EAnimals.m_sTextureNormalLogo[species].length;
        if (keepers < count) count = keepers;
        if (icons < count) count = icons;
        return count;
    }

    public static int Colour(int species, int colour) {
        return colour >= 0 && colour < Count(species) ? colour : 0;
    }

    public static String Normal(int species, int colour) {
        return EAnimals.m_sTextureNormal[species][Colour(species,colour)];
    }

    public static String Icon(int species, int colour) {
        return EAnimals.m_sTextureNormalLogo[species][Colour(species,colour)];
    }

    public static void Team(TeamData team) {
        team.SetClothesId(team.m_nAnimalClothes);
    }

    public static void Prepare(MenuChooseTeamColors menu) {
        // The stock list reuses all old buttons even when the new team has fewer
        // outfits. Remove them before the stock code creates the current list.
        menu.cColors.Clear();
        menu.m_nClothes = Colour(menu.m_nAnimal,menu.m_nClothes);
        menu.m_cTeamData.SetClothesId(menu.m_nClothes);
    }
}
