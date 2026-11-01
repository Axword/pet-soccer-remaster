/** Own controller for the unchanged native Championships2 bracket composition. */
public class CXKnockoutMenu extends SoccerUserInterface {
    public CXKnockoutMenu() {
        super();
        m_sFiles = new String[] {"data/menu/scr/CXKnockout640.scr",
            "data/menu/scr/CXKnockout.scr", "data/menu/scr/CXKnockout1024.scr"};
    }
    public void OnInit() {
        super.OnInit();
        AddToSlideIn(GetElem("ID_BACK"));
        AddToSlideIn(GetElem("ID_OK"));
        GetElem("ID_INFO_SCREEN").Hide();
        GetElem("ID_INFO_SCREEN").SetAlphaForAll(0.75f);
        ProcessKb(true);
    }
    public void Show() {
        CXKnockout.Consume();
        m_sTitle = CXKnockout.Title();
        CXKnockout.Render(this);
        super.Show();
    }
    public void OnUICommand(UIWindow control, int command) {
        super.OnUICommand(control, command);
        if (command != 0 || control == null) return;
        if ("ID_BACK".equals(control.m_sId)) CXKnockout.Back(this);
        else if ("ID_OK".equals(control.m_sId)) CXKnockout.Play(this);
    }
    void OnKeyPressed(int key, char character) {
        if (key == 1) CXKnockout.Back(this);
    }
    public void HideChampion() { GetElem("ID_INFO_SCREEN").Hide(); }
}
