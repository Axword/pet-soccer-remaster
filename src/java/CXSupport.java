/** JNI entry points implemented by src/native/cxsupport.cpp. */
public final class CXSupport {
    static { System.loadLibrary("cxsupport"); }
    public static native void Initialize();
    public static native void Tick();
    public static native int GetSelection();
    public static native void ApplyVideoSettings(GameObject argument0);
    public static native boolean ShouldIgnoreKeys(TeamController argument0);
    public static native boolean LoadFont(GameObject argument0, java.lang.String argument1, java.lang.String argument2, int argument3);
    public static native void UpdateHud(PetSoccerHud argument0);
    public static native boolean HandleUI(UIWindow argument0, UIWindow argument1, int argument2);
    public static native void RefreshOptions(UIWindow argument0);
    public static native void CloseOptions();
    public static native boolean CommentEvent(Commentator argument0, int argument1);
    public static native boolean HandleVideoKey(int argument0, boolean argument1);
    public static native int ResolveAnimal(int argument0, int argument1);
    public static native java.lang.String ResolvePlayerName(int argument0, java.lang.String argument1);
    public static native int Home(int argument0);
    public static native void SpawnBackdrop(SoccerModule argument0);
    public static native void NormalizePhysics(FootBaller argument0);
    public static native void PadFillCombo(UIComboBox argument0);
    public static native void PadShowControls(MenuOptionsControls argument0);
    public static native void PadSelectControls(MenuOptionsControls argument0, UIWindow argument1);
    public static native void PadSaveControls(MenuOptionsControls argument0);
    public static native void PadControlsFrame(MenuOptionsControls argument0);
    public static native boolean PadAllAssigned(MenuOptionsControls argument0);
    public static native boolean PadUICommand(MenuOptionsControls argument0, UIWindow argument1, int argument2);
    public static native void ConfigureController(TeamController argument0, KbSettings argument1);
    public static native boolean PadOwnsLegacyInput(TeamController argument0);
    public static native void InitializePadDefaults();
    public static native float PhysicsTerrainHeight(GameObject argument0, float argument1, float argument2);
    public static native Vector PhysicsSanitizePosition(Ball argument0, Vector argument1);
    public static native boolean PhysicsGuardBall(Ball argument0);
    public static native boolean PhysicsQAStep(int argument0);
    public static native int DisplayResolutionIndex();
    public static native int DisplayFullscreenSelection();
    public static native int ComposeDisplayPreset(int argument0, int argument1);
    public static native void BeforeCommentary(Commentator argument0, java.lang.String argument1);
    public static native void CommentaryVisual(Commentator argument0);
    public static native void TexturesChanged();
}
