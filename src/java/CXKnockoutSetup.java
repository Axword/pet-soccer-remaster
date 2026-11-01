/** Separate eight-team setup: the stock six-player league stays unchanged. */
public class CXKnockoutSetup extends MenuMultiplayer {
    public CXKnockoutSetup() {
        super();
        m_sFiles = new String[] {"data/menu/scr/CXKnockoutSetup640.scr",
            "data/menu/scr/CXKnockoutSetup.scr", "data/menu/scr/CXKnockoutSetup1024.scr"};
    }
    void OnOK() { CXKnockout.Begin(this); }
    void OnBack() { CXKnockout.Leave(); super.OnBack(); }
    void UpdateOkButton() {
        if (m_cButtonOk != null && m_cList != null)
            m_cButtonOk.SetDisabled(m_cList.GetItemCount() != 8);
    }
    void OnEditEnter() {
        if (m_cList.GetItemCount() >= 8 && FindNameInList(m_cEdit.m_sEditText) == -1) return;
        super.OnEditEnter();
        m_cEdit.SetDisabled(m_cList.GetItemCount() >= 8);
        UpdateOkButton();
    }
    void OnDelete() {
        super.OnDelete();
        m_cEdit.SetDisabled(m_cList.GetItemCount() >= 8);
        UpdateOkButton();
    }
    public void Show() {
        CXKnockout.Seed(this);
        super.Show();
        m_cList.m_ctrlScroll.Show();
        m_cEdit.SetDisabled(m_cList.GetItemCount() >= 8);
        UpdateOkButton();
    }
}
