/** Preview-only safety for the Gothic/Witcher adapters and deferred menu loads. */
public final class CXHumanPreview {
    private static final String CONTINUE = "ContinueSetFootballer";
    // Values contain only the species number, never the actor/module itself.
    // Positive = scheduled; negative = suspended until the module is shown.
    private static final java.util.WeakHashMap pending = new java.util.WeakHashMap();
    private static final String[] humans = {
        "cx_bezimienny.3da", "cx_diego.3da", "cx_gorn.3da", "cx_milten.3da",
        "cx_lester.3da", "cx_xardas.3da", "cx_thorus.3da",
        "cx_w3_geralt.3da", "cx_w3_ciri.3da", "cx_w3_yennefer.3da",
        "cx_w3_triss.3da", "cx_w3_keira.3da", "cx_w3_avallach.3da", "cx_w3_zoltan.3da"
    };

    private CXHumanPreview() {}

    public static boolean IsHuman(MenuAnimal actor) {
        if (actor == null || actor.MeshName == null) return false;
        String name = actor.MeshName.replace('\\','/');
        name = name.substring(name.lastIndexOf('/')+1);
        for (int i=0; i<humans.length; i++)
            if (name.equalsIgnoreCase(humans[i])) return true;
        return false;
    }

    public static void Configure(MenuAnimal actor) {
        if (!IsHuman(actor)) return;
        // Both are already authored in the current adapters. Robot warm-ups
        // and unretargeted audience gestures are deliberately not preview clips.
        actor.m_sIdleAnims = new String[] {"stoi_i_sapie", "stoi_rozglada_sie"};
        actor.m_sHappyIdleAnims = new String[] {"stoi_i_sapie", "stoi_rozglada_sie"};
    }

    public static void Happiness(MenuAnimal actor, boolean happy) {
        // The stock method ignores its argument. Preserve stock behaviour and
        // honour false for humans so the normal preview uses its normal pool.
        actor.m_bHappiness = IsHuman(actor) ? happy : true;
    }

    public static void Reset(MenuAnimal actor) {
        if (!IsHuman(actor)) return;
        actor.StopAnim("");
        actor.m_nRandomAnim = -1;
    }

    public static void FaceForPreview(MenuAnimal actor) {
        if (!IsHuman(actor)) return;
        Module owner=actor.GetModule();
        if (!(owner instanceof SoccerMenuShowObjectModule)) return;
        SoccerMenuShowObjectModule module=(SoccerMenuShowObjectModule)owner;
        if (Current(module)!=actor || module.m_Camera==null) return;
        Vector position=actor.GetPosition();
        Vector camera=module.m_Camera.GetPosition();
        if (position==null || camera==null) return;
        // Native captures measured local +Z == GetForwardVector for both
        // families, but their authored visible fronts differ: Gothic is -Z,
        // Witcher is +Z. The exact IsHuman guard above limits this prefix to
        // the seven accepted Witcher filenames. Never rotate model tracks.
        float x=position.fX-camera.fX,z=position.fZ-camera.fZ;
        float length2=x*x+z*z;
        if (!(length2>0.0001f) || Float.isInfinite(length2)) return;
        String mesh=actor.MeshName.replace('\\','/');
        mesh=mesh.substring(mesh.lastIndexOf('/')+1);
        if (mesh.toLowerCase().startsWith("cx_w3_")) { x=-x;z=-z; }
        Vector direction=new Vector(x,0.0f,z);
        direction.Normalize();
        actor.SetDir(direction);
    }

    static MenuAnimal Current(SoccerMenuShowObjectModule module) {
        if (module == null || module.tAnimals == null || module.m_nCurFB < 0
            || module.m_nCurFB >= module.tAnimals.length || module.m_cObject == null)
            return null;
        return module.tAnimals[module.m_nCurFB] == module.m_cObject ? module.m_cObject : null;
    }

    public static void Cancel(SoccerMenuShowObjectModule module) {
        module.DisableCallMethod(CONTINUE);
        pending.remove(module);
    }

    public static void BeforeSelection(SoccerMenuShowObjectModule module, int species) {
        // Unload deletes cached actors but retains m_nCurFB. The stock same-id
        // early return would otherwise skip initialization of a newly loaded
        // replacement and leave that human at its unstarted pose. A cache entry
        // replaced by reload can also disagree with m_cObject; never call into
        // that stale native actor while repairing the binding.
        if (species >= 44 && species <= 57 && module.m_nCurFB == species
            && module.tAnimals != null && species < module.tAnimals.length
            && (module.tAnimals[species] == null || module.tAnimals[species] != module.m_cObject)) {
            Cancel(module);
            module.m_nCurFB=-1;
            module.m_cObject=null;
            return;
        }
        Integer ticket = (Integer)pending.get(module);
        if (ticket == null) return;
        int target = Math.abs(ticket.intValue())-1;
        // A colour/repeated selection of a newly loaded actor must retain the
        // same valid deferred start; cancelling it would leave a bind pose.
        if (target == species && module.m_nCurFB == species && Current(module) != null) return;
        Cancel(module);
    }

    public static void Schedule(SoccerMenuShowObjectModule module, String name, float delay) {
        Cancel(module);
        if (Current(module) == null) return;
        if (!module.IsActive()) {
            pending.put(module,new Integer(-module.m_nCurFB-1));
            return;
        }
        pending.put(module,new Integer(module.m_nCurFB+1));
        module.CallMethodIn(name,delay);
    }

    public static void Suspend(SoccerMenuShowObjectModule module) {
        Integer ticket = (Integer)pending.get(module);
        if (ticket == null) return;
        int value = Math.abs(ticket.intValue());
        if (Current(module) == null || value != module.m_nCurFB+1) {
            Cancel(module);
            return;
        }
        module.DisableCallMethod(CONTINUE);
        pending.put(module,new Integer(-value));
    }

    public static void Resume(SoccerMenuShowObjectModule module) {
        Integer ticket = (Integer)pending.get(module);
        if (ticket == null || ticket.intValue() >= 0) return;
        if (Current(module) == null || -ticket.intValue() != module.m_nCurFB+1) {
            Cancel(module);
            return;
        }
        Schedule(module,CONTINUE,0.1f);
    }

    public static void Deferred(SoccerMenuShowObjectModule module) {
        Integer ticket = (Integer)pending.get(module);
        if (ticket == null || ticket.intValue() < 0) return;
        if (!module.IsActive()) { Suspend(module); return; }
        MenuAnimal actor = Current(module);
        if (actor == null || ticket.intValue() != module.m_nCurFB+1) {
            Cancel(module);
            return;
        }
        ShowNormal(module,actor);
    }

    public static void Immediate(SoccerMenuShowObjectModule module) {
        MenuAnimal actor = Current(module);
        if (actor == null) { Cancel(module); return; }
        if (!module.IsActive()) { Schedule(module,CONTINUE,0.1f); return; }
        ShowNormal(module,actor);
    }

    private static void ShowNormal(SoccerMenuShowObjectModule module, MenuAnimal actor) {
        Cancel(module);
        actor.ActivateOnModule();
        actor.Reset();
        actor.SetHappiness(false);
        actor.GotoPoint(actor.m_vDestinationPos);
    }

    public static void FinishCup(SoccerMenuShowObjectModule module) {
        MenuAnimal actor = Current(module);
        if (!IsHuman(actor)) return;
        Cancel(module);
        actor.ActivateOnModule();
        // SetFootballerCup already set happiness and the cup destination.
    }

    public static void FinishInstant(SoccerMenuShowObjectModule module) {
        MenuAnimal actor = Current(module);
        if (!IsHuman(actor)) return;
        Cancel(module);
        actor.ActivateOnModule();
        // GotoPointInstant stops movement directly. Complete the matching idle
        // transition now instead of leaving the running animation in place.
        actor.OnDestinationPos();
    }
}
