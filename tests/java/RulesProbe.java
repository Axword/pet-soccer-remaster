public class RulesProbe {
    static int checks;
    static SoccerMainMenuModule module = new SoccerMainMenuModule();
    static CXKnockoutSetup setup = new CXKnockoutSetup();
    static CXKnockoutMenu menu = new CXKnockoutMenu();
    static void check(boolean condition, String message) {
        checks++;
        if (!condition) throw new RuntimeException(message);
    }
    static void begin() {
        CXKnockout.Leave();
        Match.m_cMatchData=null;
        CXKnockout.Begin(setup);
        check(CXKnockout.next==0 && CXKnockout.armed && module.shown==19,"begin");
        check(!CoreLogic.m_bChampionships && CoreLogic.m_bMultiplayer,"isolated-flags");
        check(CXKnockout.pending==null && !CXKnockout.completed,"begin-clean");
    }
    static void play() {
        CXKnockout.Play(menu);
        check(CXKnockout.IsFixture(),"armed-current");
        check(Match.m_cMatchData==CXKnockout.games[CXKnockout.next],"current-game-identity");
        check(module.shown==9 && CXKnockout.ReturnUI()==19,"prematch-routing");
        MatchData game=CXKnockout.pending;
        check(CoreLogic.m_cTeamDataLeft==CXKnockout.Team(game.m_nTeamHost),"host-team");
        check(CoreLogic.m_cTeamDataRight==CXKnockout.Team(game.m_nTeamGuest),"guest-team");
        check(CoreLogic.m_nNextLevel==100+CoreLogic.m_cTeamDataLeft.m_nAnimalType,"host-map");
    }
    public static void main(String[] args) {
        setup.m_module=module;
        menu.m_module=module;
        for(int i=0;i<8;i++)setup.m_vPlayers.addElement(setup.new MpTeamRecord(new TeamData(i),"P"+i));
        Championships career=CoreLogic.player.m_cChampionships;
        career.m_nPhase=4;
        // Exhaust every possible winner branch across all seven fixtures.
        for(int mask=0;mask<128;mask++) {
            begin();
            int[] expected=new int[7];
            for(int i=0;i<7;i++) {
                int host=i<4?2*i:i<6?expected[(i-4)*2]:expected[4];
                int guest=i<4?2*i+1:i<6?expected[(i-4)*2+1]:expected[5];
                MatchData game=CXKnockout.games[i];
                check(game!=null && game.m_nTeamHost==host && game.m_nTeamGuest==guest,"round-pairing");
                play();
                boolean guestWins=(mask&(1<<i))!=0;
                game.m_nGoalsHost=guestWins?2:3;
                game.m_nGoalsGuest=guestWins?3:2;
                expected[i]=guestWins?guest:host;
                CXKnockout.Completed();
                CXKnockout.Completed();
                check(CXKnockout.completed && CXKnockout.next==i,"marker-only-no-early-advance");
                CXKnockout.Consume();
                check(CXKnockout.next==i+1 && CXKnockout.applied[i] && CXKnockout.winners[i]==expected[i],"one-correct-winner");
                check(CXKnockout.pending==null && Match.m_cMatchData==null && !CXKnockout.completed,"completion-clears");
                CXKnockout.Consume();
                check(CXKnockout.next==i+1,"duplicate-show-no-advance");
                check(game.m_nGoalsHost!=game.m_nGoalsGuest,"final-scores-retained");
            }
            check(CXKnockout.next==7 && CXKnockout.winners[6]==expected[6],"champion");
            check(CoreLogic.player.m_cChampionships==career && career.m_nPhase==4,"career-object-unmodified");
        }
        // A partial score or unplayed debug score is never sufficient.
        begin(); play();
        CXKnockout.pending.m_nGoalsHost=9;
        CXKnockout.Consume();
        check(CXKnockout.next==0 && !CXKnockout.applied[0],"no-completion-no-win");
        check(CXKnockout.games[0].m_nGoalsHost==0,"partial-score-reset");
        play();
        CXKnockout.pending.m_nGoalsHost=9;
        Match.m_cMatchData=null; // Stock Quit before match completion.
        CXKnockout.Completed();
        check(!CXKnockout.completed,"abort-null-not-complete");
        CXKnockout.Consume();
        check(CXKnockout.next==0,"abort-no-win");
        play();
        CXKnockout.Completed(); // 0:0 cannot advance.
        CXKnockout.Consume();
        check(CXKnockout.next==0,"tie-no-win");
        play();
        MatchData ours=CXKnockout.pending;
        ours.m_nGoalsHost=1;
        MatchData foreign=new MatchData(90,91);
        foreign.m_nGoalsHost=100;
        Match.m_cMatchData=foreign;
        CXKnockout.Completed();
        CXKnockout.Consume();
        check(CXKnockout.next==0 && Match.m_cMatchData==foreign,"foreign-identity-preserved");
        check(ours.m_nGoalsHost==0 && foreign.m_nGoalsHost==100,"only-own-result-reset");
        // Even an already-marked result loses eligibility if the global object changes.
        play(); CXKnockout.pending.m_nGoalsGuest=2; CXKnockout.Completed();
        Match.m_cMatchData=foreign; CXKnockout.Consume();
        check(CXKnockout.next==0,"completed-foreign-no-win");
        // Pre-match Back, including stock debug/cheated return, never awards a result.
        MenuPreMatch pre=new MenuPreMatch(); pre.m_module=module;
        for(int i=0;i<2;i++) {
            play(); CXKnockout.pending.m_nGoalsGuest=3; pre.bCheated=i==1;
            check(CXKnockout.PreMatchBack(pre),"prematch-back-handled");
            CXKnockout.Consume();
            check(CXKnockout.next==0 && !pre.bCheated && module.shown==19,"prematch-back-no-win");
        }
        play(); CXKnockout.FixReturnUI();
        check(SoccerMainMenuModule.m_nPrevUI==19,"loading-return-route");
        // Active tournament path and exact legacy career predicate, including short circuit.
        for(int armed=0;armed<2;armed++)for(int same=0;same<2;same++)
        for(int multi=0;multi<2;multi++)for(int champs=0;champs<2;champs++)
        for(int phase=-1;phase<=2;phase++) {
            CXKnockout.armed=armed!=0;
            Match.m_cMatchData=same!=0?CXKnockout.pending:foreign;
            CoreLogic.m_bMultiplayer=multi!=0; CoreLogic.m_bChampionships=champs!=0;
            career.m_nPhase=phase;
            boolean fixture=armed!=0 && same!=0 && multi!=0 && champs==0;
            int calls=CoreLogic.calls;
            check(CXKnockout.AllowGoldenGoal()==(fixture || (champs!=0 && phase>0)),"gold-truth-table");
            check(CoreLogic.calls-calls==(fixture || champs==0?0:1),"legacy-short-circuit");
        }
        CoreLogic.m_bMultiplayer=true; CoreLogic.m_bChampionships=false;
        Match.m_cMatchData=CXKnockout.pending;
        CXKnockout.Leave();
        check(!CXKnockout.armed && CXKnockout.pending==null && !CXKnockout.completed && Match.m_cMatchData==null,"leave-disarms");
        check(!CXKnockout.AllowGoldenGoal() && CXKnockout.ReturnUI()==17,"no-rule-leak");
        System.out.println("RULES_PASS checks="+checks+" complete_brackets=128 fixtures=896");
    }
}
