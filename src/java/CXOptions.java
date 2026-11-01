/** Controller for the remaster options panel. */
public class CXOptions extends SoccerUserInterface {
    public void OnUICommand(UIWindow control, int command) { CXSupport.HandleUI(this, control, command); }
    public void OnCancel() { CXSupport.CloseOptions(); }
    public void OnKeyPressed(int key, char character) { if (key == 1) CXSupport.CloseOptions(); }
}
