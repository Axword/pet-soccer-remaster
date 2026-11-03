/** Deterministic cosmetic mesh selection; leaves controls, physics and rig alone. */
public final class CXAnimalIdentity {
    private static Vector[] originalExtents=new Vector[12];
    private static String[] originalPaths=new String[12];
    /** A bounded per-species native baseline. Call before any cosmetic load. */
    public static void ensureBase(MeshObject object,int animal) {
        if(object==null||animal<0||animal>=12)return;
        String path=EAnimals.GetMeshName(animal);
        if(originalExtents[animal]!=null&&path.equals(originalPaths[animal]))return;
        object.LoadMesh(path);Vector low=new Vector(),high=new Vector();
        object.GetMeshExtents(low,high);high.Sub(low);
        originalExtents[animal]=new Vector(high);originalPaths[animal]=path;
    }
    /** Physical dimensions never come from a cosmetic variant's render bounds. */
    public static Vector physicsExtents(FootBaller player) {
        int animal=player.m_nAnimalType,reference=animal==58?0:animal;
        boolean numbered=player.m_nNumberInTeam>=0&&player.m_nNumberInTeam<7;
        if((numbered||animal==58)&&reference>=0&&reference<12&&originalExtents[reference]!=null)
            return new Vector(originalExtents[reference]);
        Vector low=new Vector(),high=new Vector();player.GetMeshExtents(low,high);high.Sub(low);return high;
    }
    public static Vector getPhysicsExtents(FootBaller player){return physicsExtents(player);}
    public static void load(MeshObject object,int animal) {
        String path=EAnimals.GetMeshName(animal);
        if(object instanceof FootBaller&&animal>=0&&animal<12) {
            FootBaller player=(FootBaller)object;int number=player.m_nNumberInTeam;
            if(number>=0&&number<7) {
                ensureBase(object,animal);
                path="data/meshes/animals/cx_ai_"+(animal<10?"0":"")+animal+"_"+number+".3da";
            }
        }
        object.LoadMesh(path);
    }
    public static void skin(MeshObject object,String texture,int material) {
        String selected=texture;
        if(object instanceof FootBaller&&texture!=null) {
            FootBaller player=(FootBaller)object;int number=player.m_nNumberInTeam;
            int animal=player.m_nAnimalType,length=texture.length();
            if(animal>=0&&animal<12&&number>=0&&number<7&&length>=8
                &&texture.startsWith("data/textures/tshirts/")&&texture.endsWith(".png")
                &&texture.charAt(length-6)=='0'&&texture.charAt(length-5)>='1'&&texture.charAt(length-5)<='5')
                selected=texture.substring(0,length-4)+"_cx"+number+".png";
        }
        object.SetSkinElement(selected,material);
    }
}
