/** One synchronous options panel; owns only its parent visibility snapshot. */
public class CXOptions extends UserInterface {
    private UserInterface previous;
    private java.util.Vector previousNodes,previousVisible;
    private boolean previousCursorVisible,opened;

    private void capture(UIWindow node) {
        previousNodes.addElement(node);
        previousVisible.addElement(new Boolean(node.m_bVisible));
        if(node.m_vChildWindows!=null)for(int i=0;i<node.m_vChildWindows.size();i++)
            capture((UIWindow)node.m_vChildWindows.elementAt(i));
    }

    private static boolean cursorVisible(UICursor cursor) {
        // UICursor.Show/Hide affect this sprite, not the cursor container.
        return cursor!=null && cursor.m_cCursorPoint!=null && cursor.m_cCursorPoint.IsVisible();
    }

    private static void cancel(UIWindow node) {
        node.DisableCallMethod("Show");
        node.DisableCallMethod("ShowElems");
        node.DisableCallMethod("StartSlideIn");
        node.DisableCallMethod("DisplayToolTip");
        if(node instanceof UIControlObject) {
            UIControlObject control=(UIControlObject)node;
            control.SetFocus(false);control.m_bFocus=false;control.m_cCurrMember=null;
        }
        if(node instanceof UIEdit) {
            UIEdit edit=(UIEdit)node;
            edit.DisableCallMethod("BlinkCursor");edit.SetCheck(false);
            if(edit.m_cCursorSprite!=null)edit.ShowTextCursor(false);
        }
    }

    private static void hideCursor(UICursor cursor) {
        if(cursor==null)return;
        cursor.DisableCallMethod("DisplayToolTip");cursor.Hide();
        if(cursor.toolTip!=null)cursor.toolTip.Hide();
    }

    /** Finish siblings even if one native window fails during cleanup. */
    private static Throwable quiet(UIWindow node,Throwable failure) {
        try {cancel(node);}catch(Throwable problem){if(failure==null)failure=problem;}
        if(node.m_vChildWindows!=null)for(int i=0;i<node.m_vChildWindows.size();i++)
            failure=quiet((UIWindow)node.m_vChildWindows.elementAt(i),failure);
        try {node.Hide();}catch(Throwable problem){if(failure==null)failure=problem;}
        if(node instanceof UserInterface)try {hideCursor(((UserInterface)node).m_currCursor);}
        catch(Throwable problem){if(failure==null)failure=problem;}
        return failure;
    }

    private static void showControls(UIWindow parent) {
        if(parent.m_vChildWindows==null)return;
        for(int i=0;i<parent.m_vChildWindows.size();i++) {
            UIWindow child=(UIWindow)parent.m_vChildWindows.elementAt(i);
            // Every control in CXOptions.scr is intended to be visible.
            child.Show();
            if(child instanceof UIStatic)((UIStatic)child).OnDisplayText();
            showControls(child);
        }
    }

    /** Native error recovery uses virtual Show on the retained modal. */
    public void Show() {
        if(previous!=null) {
            Throwable failure=quiet(previous,null);
            if(failure!=null)throw new RuntimeException("Unable to suspend options parent: "+failure);
        }
        super.Show();
        if(!m_bVisible)throw new IllegalStateException("Options root was not shown");
        showControls(this);SetFocus(true);ProcessKb(true);
        MoveTopWithChildren();
        if(m_currCursor!=null) {
            if(m_bCursorVisible)m_currCursor.Show();else m_currCursor.Hide();
            m_currCursor.MoveTop();
        }
        opened=true;
    }

    public boolean Open(UserInterface parent) {
        if(opened || previous!=null || parent==null || parent==this || !parent.m_bVisible)return false;
        if(GetElem("CX_BACK")==null || GetElem("CX_EXTRA_TEAMS")==null)return false;
        try {
            previous=parent;previousNodes=new java.util.Vector();previousVisible=new java.util.Vector();
            capture(parent);previousCursorVisible=cursorVisible(parent.m_currCursor);
            Show();return true;
        } catch(Throwable failure) {
            try {CloseToParent();}
            catch(Throwable rollbackFailure) {
                // The native caller must retain this object for recovery/retry.
                throw new RuntimeException("Options opening and rollback failed: "+rollbackFailure);
            }
            return false;
        }
    }

    public void CloseToParent() {
        opened=false;
        Throwable failure=quiet(this,null);
        // UserInterface.Hide may have registered this root in Online cleanup.
        try {CXOnlineVisibility.forget(this);}catch(Throwable problem){if(failure==null)failure=problem;}
        if(previous!=null && previousNodes!=null && previousVisible!=null) {
                // Use the actual parent override before restoring its conditional children.
                try {previous.Show();}catch(Throwable problem){if(failure==null)failure=problem;}
                for(int i=0;i<previousNodes.size();i++) {
                    UIWindow node=(UIWindow)previousNodes.elementAt(i);
                    try {
                        boolean visible=((Boolean)previousVisible.elementAt(i)).booleanValue();
                        if(visible) {
                            if(node!=previous || !node.m_bVisible)node.Show();
                            if(node instanceof UIStatic)((UIStatic)node).OnDisplayText();
                        } else node.Hide();
                    } catch(Throwable problem){if(failure==null)failure=problem;}
                }
                try {
                    previous.MoveTopWithChildren();
                    if(previous.m_currCursor!=null) {
                        if(previousCursorVisible)previous.m_currCursor.Show();else previous.m_currCursor.Hide();
                        previous.m_currCursor.MoveTop();
                    }
                } catch(Throwable problem){if(failure==null)failure=problem;}
        }
        if(failure!=null)throw new RuntimeException("Unable to restore options parent: "+failure);
        previous=null;previousNodes=null;previousVisible=null;previousCursorVisible=false;
    }

    public void OnUICommand(UIWindow control,int command) {
        if(opened && control!=null && control.m_bVisible)CXSupport.HandleUI(this,control,command);
    }
    public void OnCancel() {if(opened)CXSupport.CloseOptions();}
    public void OnKeyPressed(int key,char character) {if(opened && key==1)CXSupport.CloseOptions();}
}
