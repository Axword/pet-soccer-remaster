/** Small Online-only pause HUD. Called exclusively from the engine main thread. */
public final class CXOnlinePause extends UserInterface {
    static CXOnlinePause current;
    static SoccerModule owner;
    static SoccerModule failedOwner;
    static int width,height,lastSecond=-1;
    static boolean visible;
    UIStatic countdown;

    public void OnInit() {
        super.OnInit();ProcessMouse(false);ProcessKb(false);ProcessJoy(false);
        m_bCursorVisible=false;ShowCursor(false);SetFocus(false);
        countdown=(UIStatic)GetElem("ID_ONLINE_PAUSE_TIME");
        UIWindow frame=GetElem("ID_ONLINE_PAUSE_FRAME");
        if(frame!=null)frame.SetAlphaForAll(0.84f);
    }
    public static void update(boolean paused,int remainingMs) {
        if(!paused||remainingMs<=0||!CXOnlineMatch.isActive()) {hideOverlay();return;}
        if(SoccerGame.game==null||SoccerGame.game.activeMenu!=2){hideOverlay();return;}
        SoccerModule module=SoccerGame.GetSoccerModule();
        if(module==null){clear();return;}
        if(failedOwner==module)return;
        int w=GameObject.GetScreenWidth(),h=GameObject.GetScreenHeight();
        if(current!=null&&(owner!=module||width!=w||height!=h))clear();
        if(current==null) {
            owner=module;width=w;height=h;
            current=(CXOnlinePause)module.CreateObject("CXOnlinePause");
            if(current==null){owner=null;failedOwner=module;return;}
            int resolution=SoccerGame.GetResolution();
            String suffix=resolution==0?"640":resolution==1?"":"1024";
            if(!current.Load(module,"data/menu/scr/CXOnlinePause"+suffix+".scr",false)) {
                clear();failedOwner=module;GameObject.CrashLog("CX_ONLINE_PAUSE UI load failed");return;
            }
            current.Hide();lastSecond=-1;
        }
        int milliseconds=remainingMs>15000?15000:remainingMs;
        int seconds=(milliseconds+999)/1000;
        if(!visible) {current.Show();current.ShowCursor(false);visible=true;}
        if(seconds!=lastSecond) {
            if(current.countdown!=null) {
                current.countdown.SetText(""+seconds);current.countdown.OnDisplayText();
            }
            current.MoveTopWithChildren();lastSecond=seconds;
        }
    }
    static void hideOverlay() {
        if(current!=null&&visible)current.Hide();visible=false;lastSecond=-1;
    }
    /** Match teardown calls this before the owning module is deactivated. */
    public static void clear() {
        CXOnlinePause previous=current;SoccerModule previousOwner=owner;
        current=null;owner=null;failedOwner=null;visible=false;lastSecond=-1;width=height=0;
        if(previous==null)return;
        if(previousOwner==SoccerGame.GetSoccerModule()) {
            CXOnlineMenu.Quiet(previous);CXOnlineMenu.Forget(previous);
            previous.ReleaseTextures();previous.Remove();
            previousOwner.RemoveSprite(previous);previous.delete();
        } else CXOnlineMenu.Forget(previous);
    }
}
