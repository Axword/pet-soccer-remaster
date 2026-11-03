import java.util.Vector;

/** Scoped Online cleanup. Ordinary offline visibility keeps its native behavior. */
public final class CXOnlineVisibility {
    static Vector hidden=new Vector();
    static int depth;
    static final class Hidden {
        UserInterface root;Vector nodes=new Vector(),visible=new Vector();
        Hidden(UserInterface value){root=value;capture(value);}
        void capture(UIWindow parent){
            if(parent.m_vChildWindows==null)return;
            for(int i=0;i<parent.m_vChildWindows.size();i++){
                UIWindow child=(UIWindow)parent.m_vChildWindows.elementAt(i);
                nodes.addElement(child);visible.addElement(new Boolean(child.m_bVisible));capture(child);
            }
        }
        void restore(){
            for(int i=0;i<nodes.size();i++){
                UIWindow child=(UIWindow)nodes.elementAt(i);
                if(((Boolean)visible.elementAt(i)).booleanValue())child.Show();else child.Hide();
            }
        }
    }
    static Hidden saved(UserInterface root){
        for(int i=0;i<hidden.size();i++){Hidden item=(Hidden)hidden.elementAt(i);if(item.root==root)return item;}
        return null;
    }
    static void cancel(UIWindow node){
        node.DisableCallMethod("Show");node.DisableCallMethod("ShowElems");
        node.DisableCallMethod("StartSlideIn");node.DisableCallMethod("DisplayToolTip");
        if(node instanceof UIControlObject){
            UIControlObject control=(UIControlObject)node;control.SetFocus(false);
            control.m_bFocus=false;control.m_cCurrMember=null;
        }
        if(node instanceof UIEdit){
            UIEdit edit=(UIEdit)node;edit.DisableCallMethod("BlinkCursor");edit.SetCheck(false);edit.ShowTextCursor(false);
        }
    }
    static void children(UIWindow parent){
        if(parent.m_vChildWindows==null)return;
        for(int i=0;i<parent.m_vChildWindows.size();i++){
            UIWindow child=(UIWindow)parent.m_vChildWindows.elementAt(i);
            cancel(child);children(child);child.Hide();
        }
    }
    /** Invoked after native Hide. Visibility snapshots are taken only once. */
    public static void hidden(UserInterface root){
        if(root==null)return;
        if(!(root instanceof CXOnlineMenu)&&depth==0&&!CXOnlineMatch.isActive()
            &&SoccerMainMenuModule.m_nCurUI!=CXOnlineMenu.UI_ONLINE&&saved(root)==null)return;
        if(saved(root)==null)hidden.addElement(new Hidden(root));
        cancel(root);children(root);
        if(root.m_currCursor!=null)root.m_currCursor.Hide();
    }
    /** Invoked before native Show, restoring only the currently selected screen. */
    public static boolean show(UserInterface root){
        Hidden item=saved(root);if(item==null)return true;
        if(root.m_module instanceof SoccerMainMenuModule){
            SoccerMainMenuModule module=(SoccerMainMenuModule)root.m_module;
            for(int i=0;i<module.m_tUIs.length;i++)if(module.m_tUIs[i]==root&&i!=SoccerMainMenuModule.m_nCurUI)return false;
        }
        hidden.removeElement(item);item.restore();return true;
    }
    public static void quiet(UIWindow root){
        if(root==null)return;depth++;
        try{cancel(root);if(root instanceof UserInterface)root.Hide();else{children(root);root.Hide();}}
        finally{depth--;}
    }
    public static void all(SoccerMainMenuModule module){
        if(module==null||module.m_tUIs==null)return;
        for(int i=0;i<module.m_tUIs.length;i++)if(module.m_tUIs[i]!=null)quiet(module.m_tUIs[i]);
    }
    /** Final module disposal only. Does not restore controls, callbacks or cursors. */
    public static void forget(UIWindow root){
        if(root==null)return;
        for(int i=hidden.size()-1;i>=0;i--)if(((Hidden)hidden.elementAt(i)).root==root)hidden.removeElementAt(i);
    }
}
