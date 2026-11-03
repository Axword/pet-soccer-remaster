import java.io.IOException;
import java.util.Hashtable;

/** Owned Online 1v1 adapter. All public hooks run on the engine's main thread. */
public final class CXOnlineMatch {
    private static boolean active, host, injecting, configured, exiting, guestReady;
    private static int matchId, sequence, inputSequence, appliedSequence=-1, receivedSequence=-1;
    private static int moveMask, buttonMask, spacePress, lastSpace;
    private static int[] presses=new int[4], lastPresses=new int[4];
    private static AIFootBaller[] pendingPass=new AIFootBaller[2];
    private static int[] pendingPassState=new int[2];
    private static long lastSnapshot, lastInput, lastReceived, bootAt;
    private static SoccerModule module;
    // Stable participant identities. Stock halftime swaps Match.m_teams indices.
    private static Team[] teams=new Team[2]; // [host participant, guest participant]
    private static PlayerSave previousPlayer;
    private static boolean previousMultiplayer, previousDemo, previousChampionship;
    private static TeamData previousLeft, previousRight;
    private static MatchData previousMatchData;
    private static MatchData sessionMatchData;
    private static int hostTeamId, guestTeamId;
    private static boolean finished, finalSnapshotQueued, completionSubmitted, returnPending;
    private static int finalHostGoals, finalGuestGoals;
    private static long returnRequestedAt;
    private static boolean pauseActive,pauseResumeTimer,pausePreviousFlag,pausePreviousCameraFreeze,escapeDown,spaceDown,blockedSpace,remoteResumeBaseline;
    private static int blockedButtons,blockedDirections,blockedAxes;
    private static long pauseStartedAt;
    private static int previousLevel;
    private static Hashtable animations=new Hashtable();
    private static Hashtable heldPhysics=new Hashtable();
    private static boolean heldClockRunning;
    private static int animSerial;
    private static int hudEvent=-1,hudSerial,appliedHudSerial;
    private static String status="";
    public static int snapshotsSent, snapshotsApplied, inputsApplied;

    public static boolean isActive(){return active;}
    public static boolean isGuest(){return active&&!host;}
    public static boolean isHost(){return active&&host;}
    public static boolean shouldSkipSimulation(){return isGuest()||paused();}
    public static String getStatus(){return status;}
    private static boolean validTeam(int id){return id>=0&&id<=11||id==30||id==37||id==44||id==51||id==58;}

    public static void start(SoccerMainMenuModule menu, boolean hosting, int left, int right) {
        if(active || menu==null || !CXOnlineTransport.isMatchStarted() || !validTeam(left) || !validTeam(right))return;
        previousPlayer=CoreLogic.GetPlayer();
        previousMultiplayer=CoreLogic.m_bMultiplayer;previousDemo=CoreLogic.m_bDemo;
        previousChampionship=CoreLogic.m_bChampionships;previousLeft=CoreLogic.m_cTeamDataLeft;
        previousRight=CoreLogic.m_cTeamDataRight;previousLevel=CoreLogic.m_nNextLevel;previousMatchData=Match.m_cMatchData;
        PlayerSave session=new PlayerSave();session.SetDefault();
        if(previousPlayer!=null){
            session.m_Name=previousPlayer.m_Name;session.m_Kb0=previousPlayer.m_Kb0;session.m_Kb1=previousPlayer.m_Kb1;
            session.m_nDiffLevel=previousPlayer.m_nDiffLevel;session.m_nDiffSetting=previousPlayer.m_nDiffSetting;
            session.m_bAudienceOn=previousPlayer.m_bAudienceOn;session.m_bFieldMapOn=previousPlayer.m_bFieldMapOn;
            session.m_bCommentatorOn=previousPlayer.m_bCommentatorOn;
            session.m_nDefCameraMode=previousPlayer.m_nDefCameraMode;
            session.m_fCamZoomHoriz=previousPlayer.m_fCamZoomHoriz;session.m_fCamZoomHorizSat=previousPlayer.m_fCamZoomHorizSat;
            session.m_fCamZoomVert=previousPlayer.m_fCamZoomVert;session.m_fCamZoomVertSat=previousPlayer.m_fCamZoomVertSat;
        }
        // Session only: one-minute match preset and no unsynchronized replay camera.
        session.m_nMatchHalfTimeIndex=4;session.m_bReplaysOn=false;
        CoreLogic.SetPlayer(session);CoreLogic.m_bMultiplayer=true;CoreLogic.m_bDemo=false;CoreLogic.m_bChampionships=false;
        CoreLogic.m_cTeamDataLeft=new TeamData(ETeams.GetTeamData(left));
        CoreLogic.m_cTeamDataRight=new TeamData(ETeams.GetTeamData(right));
        CoreLogic.m_nNextLevel=ETeams.GetHomeField(left);
        Match.m_cMatchData=sessionMatchData=new MatchData(left,right);hostTeamId=left;guestTeamId=right;
        active=true;host=hosting;configured=false;exiting=false;guestReady=false;module=null;teams=new Team[2];
        clearPause(false);escapeDown=false;spaceDown=false;blockedSpace=false;blockedButtons=blockedDirections=blockedAxes=0;remoteResumeBaseline=false;
        finished=false;finalSnapshotQueued=false;completionSubmitted=false;returnPending=false;returnRequestedAt=0;
        matchId=CXOnlineTransport.getMatchId();sequence=0;inputSequence=0;appliedSequence=-1;receivedSequence=-1;
        moveMask=0;buttonMask=0;spacePress=0;lastSpace=0;presses=new int[4];lastPresses=new int[4];
        pendingPass=new AIFootBaller[2];pendingPassState=new int[2];
        animations.clear();heldPhysics.clear();heldClockRunning=false;animSerial=0;hudEvent=-1;hudSerial=0;appliedHudSerial=0;
        snapshotsSent=0;snapshotsApplied=0;inputsApplied=0;
        bootAt=lastReceived=System.currentTimeMillis();lastSnapshot=lastInput=0;status="Loading Online 1v1";
        GameObject.CrashLog("CX_ONLINE_START host="+host+" match="+matchId+" teams="+left+","+right);
        // The stock pre-match OK button sends multiplayer to its local league.
        // Keep the two-human control flag, but enter the normal level directly.
        CXOnlineMenu.SuspendAll(menu);SoccerGame.game.RunModule();
    }
    public static void handle(CXOnlineTransport.Event event) {
        if(!active||event==null)return;
        if(event.type==CXOnlineTransport.DISCONNECTED || event.type==CXOnlineTransport.LEFT){
            // Real transport resets started and its mailbox before LEFT.
            // A late poll cannot recover completion after that room reset.
            if(!host&&configured)receiveSnapshots();
            end("Connection closed",false);
        }
    }
    public static void globalTick() {
        CXOnlineMenu.Pump();
        updatePause();
        if(active&&finished)flushCompletion();
        if(active&&returnPending&&!deferReturnToMenu())end("Match completed",true);
        if(active && !exiting && (!CXOnlineTransport.isConnected() || !CXOnlineTransport.isMatchStarted()))
            end("Connection closed",false);
    }
    public static void end(String reason, boolean leave) {
        if(!active||exiting)return;
        if(leave&&deferReturnToMenu()){status="Saving completed match";return;}
        clearPause(true);
        exiting=true;status=reason;
        GameObject.CrashLog("CX_ONLINE_END "+reason+" sent="+snapshotsSent+" applied="+snapshotsApplied+" inputs="+inputsApplied);
        if(leave)CXOnlineTransport.leaveRoom();
        quietMatchMenu();
        if(SoccerGame.game!=null && SoccerGame.game.activeMenu==2)SoccerGame.game.ExitToMenu();
        returnedToMenu();
    }
    public static void returnedToMenu() {
        if(!active)return;
        clearPause(false);
        CXOnlineMenu.SuspendAll(SoccerGame.firstMenuModule);
        active=false;configured=false;module=null;teams=new Team[2];pendingPass=new AIFootBaller[2];animations.clear();heldPhysics.clear();
        sessionMatchData=null;finished=false;finalSnapshotQueued=false;completionSubmitted=false;returnPending=false;
        if(previousPlayer!=null)CoreLogic.SetPlayer(previousPlayer);else CoreLogic.m_cCurPlayer=null;
        CoreLogic.m_bMultiplayer=previousMultiplayer;CoreLogic.m_bDemo=previousDemo;
        CoreLogic.m_bChampionships=previousChampionship;CoreLogic.m_cTeamDataLeft=previousLeft;
        CoreLogic.m_cTeamDataRight=previousRight;CoreLogic.m_nNextLevel=previousLevel;Match.m_cMatchData=previousMatchData;
        if(CXOnlineTransport.isMatchStarted())CXOnlineTransport.leaveRoom();
        if(SoccerGame.firstMenuModule!=null)SoccerGame.firstMenuModule.ShowUI(20);
        exiting=false;
    }
    public static void beforeReturnToMenu(){
        if(!active)return;
        clearPause(true);
        // Loading a two-human match selects the stock league return UI. Replace
        // that target before the native menu activation can enqueue its Show.
        SoccerMainMenuModule.m_nPrevUI=20;
        quietMatchMenu();CXOnlineMenu.SuspendAll(SoccerGame.firstMenuModule);
        if(SoccerGame.game!=null&&SoccerGame.game.GetCommentator()!=null)
            SoccerGame.game.GetCommentator().DisableCallMethod("CommentMatchEnd");
    }
    private static void quietMatchMenu(){
        if(module==null||module.m_cMenuInGameModule==null)return;
        SoccerInGameMenuModule menu=module.m_cMenuInGameModule;
        if(menu.m_cMenuInGame!=null){CXOnlineMenu.Quiet(menu.m_cMenuInGame);CXOnlineMenu.Quiet(menu.m_cMenuInGame.m_cYesNo);}
        CXOnlineMenu.Quiet(menu.m_cMenuYesNo);
        if(module.m_bMenuVisible){module.m_bMenuVisible=false;menu.Deactivate();}
        // Final exit only: native deactivation can add its own Hide snapshot.
        // Release transient roots afterward; main-menu snapshots stay restorable.
        if(menu.m_cMenuInGame!=null){CXOnlineMenu.Forget(menu.m_cMenuInGame);CXOnlineMenu.Forget(menu.m_cMenuInGame.m_cYesNo);}
        CXOnlineMenu.Forget(menu.m_cMenuYesNo);
    }
    /** Native ExitToMenu entry guard; waiting continues through normal frames. */
    public static boolean deferReturnToMenu(){
        if(!active||exiting||!finished||!CXOnlineTransport.isConnected()||!CXOnlineTransport.isMatchStarted())return false;
        flushCompletion();
        int result=CXOnlineTransport.getResultStatus(matchId);
        if(result==2||result==3)return false;
        long now=System.currentTimeMillis();
        if(!returnPending){returnPending=true;returnRequestedAt=now;}
        return now-returnRequestedAt<3000;
    }
    /** Called only after the actual native OnMatchEnd body has reached STATE_END. */
    public static void onMatchEnd(SoccerModule m){
        AIMatch match=SoccerModule.m_cMatch;
        if(!isHost()||!configured||exiting||finished||m!=module||match==null
            ||!match.m_bMatchEnding||AIMatch.GetMatchState()!=3||match.m_nHalfNo!=1
            ||m.m_Clock==null||m.m_Clock.GetMatchTimeF()<60||Match.m_cMatchData!=sessionMatchData
            ||sessionMatchData==null||sessionMatchData.m_nTeamHost!=hostTeamId||sessionMatchData.m_nTeamGuest!=guestTeamId)return;
        // OnGoal explicitly accounts for half parity. These counters stay in
        // original MatchData host/guest order when m_teams swaps at halftime.
        finalHostGoals=match.m_nScoreLeft;finalGuestGoals=match.m_nScoreRight;
        if(finalHostGoals<0||finalHostGoals>999||finalGuestGoals<0||finalGuestGoals>999)return;
        finished=true;flushCompletion();
        GameObject.CrashLog("CX_ONLINE_COMPLETED match="+matchId+" score="+finalHostGoals+","+finalGuestGoals);
    }
    private static void flushCompletion(){
        if(!active||!finished||completionSubmitted)return;
        if(host&&!finalSnapshotQueued){
            try{finalSnapshotQueued=CXOnlineTransport.sendFinalSnapshot(CXOnlineState.encode(capture()));
                if(finalSnapshotQueued)snapshotsSent++;}
            catch(IOException bad){status="Final snapshot unavailable";}
            if(!finalSnapshotQueued)return;
        }
        completionSubmitted=CXOnlineTransport.submitMatchResult(matchId,finalHostGoals,finalGuestGoals);
    }
    private static void receiveSnapshots(){
        byte[] data;
        while((data=CXOnlineTransport.pollSnapshot())!=null){
            try{CXOnlineState.Frame f=CXOnlineState.decode(data);if(f.matchId==matchId&&f.sequence>appliedSequence)applySnapshot(f);}
            catch(IOException bad){status="Rejected invalid snapshot";}
        }
    }
    public static boolean moduleKey(SoccerModule m,int key,boolean down,char character) {
        if(!active||injecting)return false;
        if(key==1){
            if(down&&!escapeDown&&configured&&!finished&&!exiting&&(host?guestReady:snapshotsApplied>0))CXOnlineTransport.requestPause();
            escapeDown=down;return true;
        }
        if(key==57){
            spaceDown=down;
            if(paused()||waitingForHost()){blockedSpace=down;return true;}
            if(blockedSpace){if(!down)blockedSpace=false;return true;}
        }
        if(paused())return true;
        if(!host){
            if(key==57 && down){spacePress++;sendInput();}
            return true;
        }
        return false;
    }
    private static boolean paused(){
        return active&&(pauseActive||CXOnlineTransport.getPauseMatchId()==matchId&&CXOnlineTransport.isPaused());
    }
    private static boolean waitingForHost(){return isGuest()&&configured&&snapshotsApplied==0;}
    /** The stock ShowMenu/HideMenu use this module's TimerStop/TimerStart.
     * Its native simulation, animation and callback clock stop together; the
     * separate SoccerGame.OnFrame still pumps sockets and the wall-time expiry. */
    private static void updatePause(){
        if(!active||!configured||module==null){CXOnlinePause.clear();return;}
        boolean wanted=!finished&&!exiting&&CXOnlineTransport.getPauseMatchId()==matchId&&CXOnlineTransport.isPaused();
        long now=System.currentTimeMillis();
        if(wanted&&!pauseActive){
            pauseActive=true;pauseStartedAt=now;pausePreviousFlag=module.bPaused;
            pauseResumeTimer=!module.m_bMenuVisible&&!module.bPaused;
            TeamController local=localController();int held=(local==null?0:local._KEY_STATES)|moveMask;
            blockedButtons=buttonMask;blockedDirections=held;blockedAxes=((held&10)!=0?1:0)|((held&5)!=0?2:0);blockedSpace=spaceDown;
            moveMask=buttonMask=0;pendingPass=new AIFootBaller[2];remoteResumeBaseline=host;
            for(int t=0;t<2;t++)if(teams[t]!=null&&teams[t].m_cTeamController!=null)teams[t].m_cTeamController.Clear();
            SoccerCamera camera=module.GetSoccerCamera();pausePreviousCameraFreeze=camera!=null&&camera.m_bFreezed;
            if(camera!=null)camera.Freeze();
            module.bPaused=true;module.TimerStop();status="Paused";
            GameObject.CrashLog("CX_ONLINE_PAUSE match="+matchId);
        } else if(!wanted&&pauseActive){
            clearPause(true);
            if(!host)sendInput();
        }
        if(pauseActive){
            // Keep network inactivity independent of the stopped module clock.
            lastReceived=lastInput=lastSnapshot=now;
            int[] input;while(host&&(input=CXOnlineTransport.pollInput())!=null)discardPausedInput(input);
        }
        CXOnlinePause.update(pauseActive,pauseActive?CXOnlineTransport.getPauseRemainingMillis():0);
    }
    private static void clearPause(boolean resume){
        if(pauseActive&&resume&&module!=null){
            module.bPaused=pausePreviousFlag;
            if(pauseResumeTimer)module.TimerStart();
            SoccerCamera camera=module.GetSoccerCamera();if(camera!=null&&!pausePreviousCameraFreeze)camera.UnFreeze();
            float now=module.GetTime();module.m_fNowTime=module.m_fLastUpdateTime=now;module.m_fFrameTime=0;
            for(int t=0;t<2;t++)if(teams[t]!=null&&teams[t].m_cFocusFBaller!=null)teams[t].m_cFocusFBaller.UpdateMovement();
            long wall=System.currentTimeMillis();bootAt+=Math.max(0,wall-pauseStartedAt);lastReceived=wall;lastInput=lastSnapshot=0;
            status="Online 1v1";GameObject.CrashLog("CX_ONLINE_RESUME match="+matchId);
        }
        pauseActive=false;pauseResumeTimer=false;pauseStartedAt=0;CXOnlinePause.clear();
    }
    private static void discardPausedInput(int[] data){
        if(!validInput(data,true))return;
        receivedSequence=data[2];for(int i=0;i<4;i++)lastPresses[i]=data[4+i];lastSpace=data[8];
    }
    private static boolean setup(SoccerModule m) {
        AIMatch match=SoccerModule.m_cMatch;
        if(match==null || !match.m_bInited || m.m_Clock==null || GameField.m_cBall==null || match.GetReferee()==null
            || match.GetTeam(0)==null || match.GetTeam(1)==null || match.GetTeam(0).GetFootBallerCount()<1
            || match.GetTeam(1).GetFootBallerCount()<1)return false;
        module=m;
        if(!configured) {
            teams[0]=match.GetTeam(0);teams[1]=match.GetTeam(1);
            Team remote=teams[host?1:0], local=teams[host?0:1];
            // Physical keyboard/gamepad 1 belongs to the local human on either machine.
            local.m_cTeamController.Init((AITeam)local,SoccerGame.GetKb0());local.UpdateKeyCodes();
            KbSettings dummy=new KbSettings(1);dummy.m_Device=0;
            remote.m_cTeamController.Init((AITeam)remote,dummy);remote.UpdateKeyCodes();
            remote.m_cTeamController.CXInputPort=-1;
            remote.m_cTeamController.UnregisterKeyRequest();remote.m_cTeamController.UnregisterJoyAxisRequest();
            remote.m_cTeamController.UnregisterJoyButtonRequest();remote.m_cTeamController.Clear();
            syncPlayerTeams();
            configured=true;status=host?"Waiting for opponent":"Receiving match";
            if(!host) {
                m.DisableCallMethod("StartGameDelay");m.DisableCallMethod("StartMatch");
                match.ActivateAIs(false);m.m_Clock.Stop();freezeActors(match);
                m.StartFadeIn();m.ShowHud();sendInput();
            }
            GameObject.CrashLog("CX_ONLINE_LOADED host="+host+" players="+match.GetTeam(0).GetFootBallerCount()+","+match.GetTeam(1).GetFootBallerCount());
        }
        syncPlayerTeams();
        return true;
    }
    /** true skips stock simulation only for a connected guest. */
    public static boolean beforeFrame(SoccerModule m) {
        if(!active)return false;
        if(!setup(m))return !host;
        updatePause();if(pauseActive)return true;
        long now=System.currentTimeMillis();
        if(host) {
            int[] input;
            while((input=CXOnlineTransport.pollInput())!=null)applyInput(input);
            flushPendingPass();
            if(guestReady && now-lastReceived>1500)applyMovement(0);
            if(!guestReady && now-bootAt>60000){end("Opponent did not finish loading",true);return true;}
            if(!guestReady){
                m.m_fNowTime=m.GetTime();m.m_fLastUpdateTime=m.m_fNowTime;m.m_fFrameTime=0;
                if(!m.m_Clock.m_bStop)heldClockRunning=true;
                m.m_Clock.Stop();holdActors(SoccerModule.m_cMatch);return true;
            }
            return false;
        }
        receiveSnapshots();
        if(now-lastInput>=200)sendInput();
        if(snapshotsApplied>0&&now-lastReceived>2000)status="Waiting for host";
        // Keep the last authoritative frame still during a network pause.
        float previous=m.m_fLastUpdateTime;
        m.m_fNowTime=m.GetTime();m.m_fLastUpdateTime=m.m_fNowTime;m.m_fFrameTime=m.m_fNowTime-previous;
        if(m.m_fFrameTime<0||m.m_fFrameTime>.2f)m.m_fFrameTime=.016f;
        if(m.m_fFadeTime>0){
            if(m.m_nFadeMode==1)m.Fade(.9f,1/m.m_fFadeTime,m.m_fFrameTime);
            else if(m.m_nFadeMode==2)m.Fade(0,-1/m.m_fFadeTime,m.m_fFrameTime);
        }
        m.m_Clock.m_bStop=true;freezeActors(SoccerModule.m_cMatch);
        return true;
    }
    public static void afterFrame(SoccerModule m) {
        if(!active||!host||!configured||paused())return;
        syncPlayerTeams();
        if(finished){flushCompletion();return;}
        long now=System.currentTimeMillis();if(now-lastSnapshot<50)return;lastSnapshot=now;
        try{if(CXOnlineTransport.sendSnapshot(CXOnlineState.encode(capture())))snapshotsSent++;}
        catch(IOException bad){status="Snapshot unavailable";}
    }
    private static TeamController localController(){
        return configured&&teams[host?0:1]!=null?teams[host?0:1].m_cTeamController:null;
    }
    private static int teamIndex(Team team){return SoccerModule.m_cMatch.GetTeam(0)==team?0:1;}
    private static void syncPlayerTeams(){
        AIMatch m=SoccerModule.m_cMatch;
        m.m_nPlayer1Team=teamIndex(teams[host?0:1]);m.m_nPlayer2Team=teamIndex(teams[host?1:0]);
    }
    private static int buttonIndex(int type){return type==0?0:type==1?1:type==2?2:type==4?3:-1;}
    private static boolean specialPassReady(AIFootBaller taker){
        AIMatch m=SoccerModule.m_cMatch;
        // UpdateSpecialBall sets Done when the taker reaches the restart point,
        // before the kick request. Mirror the actual event-22 acceptance gates.
        return m.m_bGoneToSpecialBall&&m.m_bSpecialBallDone&&taker.HasBall()&&taker.HasSpecialGoal()
            &&taker.m_bActiveAI&&!taker.IsIdle()&&!taker.IsDefence()&&taker.CanGoalBreak()
            &&(AIMatch.GetMatchState()!=7||m.m_bStartGameWhistleDone)
            &&taker.m_cAISystem!=null&&taker.m_cAISystem.CheckEvent(taker,22);
    }
    private static boolean deferSpecialPass(InputDigital action,int device,int key,boolean down){
        if(!host||action.m_iActionType!=0||!down||device!=action.m_iDeviceType
            ||(key!=action.m_iKeyValue&&action.m_iKeyValue!=255))return false;
        AIMatch m=SoccerModule.m_cMatch;int state=AIMatch.GetMatchState();
        AIFootBaller taker=m.m_cSpecialFB;
        if(state<4||state>7||taker==null||taker.m_cTeam!=action.m_controller.m_cTeam
            ||!taker.HasSpecialGoal()||!taker.HasBall())return false;
        int participant=taker.m_cTeam==teams[0]?0:1;
        if(specialPassReady(taker)){pendingPass[participant]=null;return false;}
        if(pendingPass[participant]!=taker)GameObject.CrashLog("CX_ONLINE_PASS_BUFFER state="+state+" participant="+participant);
        pendingPass[participant]=taker;pendingPassState[participant]=state;return true;
    }
    private static void flushPendingPass(){
        AIMatch m=SoccerModule.m_cMatch;int state=AIMatch.GetMatchState();
        for(int i=0;i<2;i++){
            AIFootBaller taker=pendingPass[i];if(taker==null)continue;
            if(state!=pendingPassState[i]||m.m_cSpecialFB!=taker){pendingPass[i]=null;continue;}
            if(!specialPassReady(taker))continue;
            pendingPass[i]=null;InputAction action=teams[i].m_cTeamController.m_Actions[0];
            if(action instanceof InputDigital){
                InputDigital d=(InputDigital)action;injecting=true;
                try{d.Translate(d.m_iDeviceType,d.m_iKeyValue,true);}
                finally{injecting=false;}
                GameObject.CrashLog("CX_ONLINE_PASS_DISPATCH state="+state+" participant="+i);
            }
        }
    }
    public static boolean digital(InputDigital a,int device,int key,boolean down) {
        if(!active||!configured)return false;
        if(!injecting&&a.m_controller==localController()&&device==a.m_iDeviceType){
            int b=buttonIndex(a.m_iActionType),bit=b<0?0:1<<b;
            boolean button=bit!=0&&(key==a.m_iKeyValue||a.m_iKeyValue==255);
            int direction=(a.m_iActionType==3||a.m_iActionType==5)?(key==a.m_nUpKey?1:key==a.m_nRightKey?2:key==a.m_nDownKey?4:key==a.m_nLeftKey?8:0):0;
            if(paused()||waitingForHost()){
                if(button)blockedButtons=down?blockedButtons|bit:blockedButtons&~bit;
                if(direction!=0)blockedDirections=down?blockedDirections|direction:blockedDirections&~direction;
                return true;
            }
            if(button&&(blockedButtons&bit)!=0){if(!down)blockedButtons&=~bit;return true;}
            if(direction!=0&&(blockedDirections&direction)!=0){if(!down)blockedDirections&=~direction;return true;}
            if(host&&button)buttonMask=down?buttonMask|bit:buttonMask&~bit;
        }
        if(paused())return true;
        if(host&&(injecting||a.m_controller==localController())&&deferSpecialPass(a,device,key,down))return true;
        if(injecting)return false;
        if(a.m_controller!=localController())return true;
        if(host)return false;
        if(device!=a.m_iDeviceType)return true;
        int type=a.m_iActionType;
        if(type==3||type==5) {
            int bit=key==a.m_nUpKey?1:key==a.m_nRightKey?2:key==a.m_nDownKey?4:key==a.m_nLeftKey?8:0;
            if(bit!=0){moveMask=down?moveMask|bit:moveMask&~bit;sendInput();}
        } else if(key==a.m_iKeyValue || a.m_iKeyValue==255) {
            int b=buttonIndex(type);if(b>=0){int bit=1<<b;
                if(down&&(buttonMask&bit)==0)presses[b]++;
                buttonMask=down?buttonMask|bit:buttonMask&~bit;sendInput();}
        }
        return true;
    }
    public static boolean analog(InputAnalog a,int device,int axis,float value) {
        if(!active||injecting||!configured)return false;
        if(a.m_controller!=localController())return true;
        if(device==a.m_iDeviceType&&(axis==0||axis==1)){
            int bit=1<<axis;boolean neutral=value>=-.1f&&value<=.1f;
            if(paused()||waitingForHost()){if(neutral)blockedAxes&=~bit;else blockedAxes|=bit;return true;}
            if((blockedAxes&bit)!=0){if(neutral)blockedAxes&=~bit;return true;}
        }
        if(paused())return true;
        if(host)return false;
        if(device!=a.m_iDeviceType || value!=value || value>1.1f || value< -1.1f)return true;
        if(a.m_iActionType==3||a.m_iActionType==5) {
            if(axis==0)moveMask=(moveMask&~10)|(value< -.1f?8:value>.1f?2:0);
            if(axis==1)moveMask=(moveMask&~5)|(value< -.1f?1:value>.1f?4:0);
            sendInput();
        }
        return true;
    }
    private static void sendInput(){
        if(!isGuest()||!configured||paused())return;
        // A single ready packet starts the host. Wait for its first frame
        // before heartbeats can fill the mailbox while its map is loading.
        if(snapshotsApplied==0&&inputSequence>0)return;
        int next=inputSequence+1;
        if(CXOnlineTransport.sendInput(new int[]{CXOnlineState.MAGIC,matchId,next,moveMask,
            presses[0],presses[1],presses[2],presses[3],spacePress,1})){
            inputSequence=next;lastInput=System.currentTimeMillis();
        }
    }
    private static boolean validInput(int[] data,boolean baseline){
        if(data.length!=10||data[0]!=CXOnlineState.MAGIC||data[1]!=matchId||data[2]<=receivedSequence
            ||data[3]<0||data[3]>15||data[9]!=1)return false;
        for(int i=0;i<4;i++)if(data[4+i]<lastPresses[i]||!baseline&&data[4+i]-lastPresses[i]>16)return false;
        return data[8]>=lastSpace&&(baseline||data[8]-lastSpace<=16);
    }
    private static void applyInput(int[] data) {
        if(!validInput(data,remoteResumeBaseline))return;
        if(remoteResumeBaseline){discardPausedInput(data);remoteResumeBaseline=false;lastReceived=System.currentTimeMillis();applyMovement(0);return;}
        receivedSequence=data[2];lastReceived=System.currentTimeMillis();
        if(!guestReady){releaseHeldActors();if(heldClockRunning)module.m_Clock.Start();}
        guestReady=true;status="Online 1v1";
        applyMovement(data[3]);
        TeamController c=teams[1].m_cTeamController;
        int[] types={0,1,2,4};
        injecting=true;
        try{
            for(int b=0;b<4;b++)if(data[4+b]!=lastPresses[b]){
                lastPresses[b]=data[4+b];InputAction a=c.m_Actions[types[b]];
                if(a instanceof InputDigital){InputDigital d=(InputDigital)a;d.Translate(d.m_iDeviceType,d.m_iKeyValue,true);}
            }
            if(data[8]!=lastSpace){lastSpace=data[8];module.OnInputKey(57,true,' ');}
        }finally{injecting=false;}
        inputsApplied++;
    }
    private static void applyMovement(int mask) {
        AITeam team=(AITeam)teams[1];
        TeamController c=team.m_cTeamController;
        if(c._KEY_STATES!=mask){c._KEY_STATES=mask;if(team.m_cFocusFBaller!=null)team.m_cFocusFBaller.UpdateMovement();}
        SelectionDest sel=SoccerModule.m_cMatch.cSpecialBallSel;
        if(sel!=null&&sel.IsActive()&&sel.m_cTeam==team)sel.UpdateMovement();
    }
    public static void animation(FootBaller fb,String name,int flags) {
        if(!active||!host||name==null||name.length()>80)return;
        animations.put(fb,new Object[]{name,new Integer(flags),new Integer(++animSerial)});
    }
    public static void hudEvent(int event){
        if(isHost()&&event>=0&&event<=2){hudEvent=event;hudSerial++;}
    }
    private static CXOnlineState.Actor actor(ControlObject object) {
        CXOnlineState.Actor a=new CXOnlineState.Actor();
        Vector p=object.GetPosition(),f=object.GetForwardVector(),u=object.GetUpVector();
        a.transform=new float[]{p.fX,p.fY,p.fZ,f.fX,f.fY,f.fZ,u.fX,u.fY,u.fZ};
        Object[] anim=(Object[])animations.get(object);
        if(anim!=null){a.animation=(String)anim[0];a.animationFlags=((Integer)anim[1]).intValue();a.animationSerial=((Integer)anim[2]).intValue();}
        return a;
    }
    private static int index(Team team,FootBaller fb){for(int i=0;i<team.GetFootBallerCount();i++)if(team.GetFootBaller(i)==fb)return i;return -1;}
    private static CXOnlineState.Frame capture() {
        AIMatch m=SoccerModule.m_cMatch;CXOnlineState.Frame f=new CXOnlineState.Frame();
        f.matchId=matchId;f.sequence=sequence++;f.state=AIMatch.GetMatchState();f.half=m.m_nHalfNo;
        f.leftScore=m.m_nScoreLeft;f.rightScore=m.m_nScoreRight;f.clock=module.m_Clock.GetMatchTimeF();f.playing=Match.m_bPlaying;
        f.finished=finished;
        if(finished){f.state=3;f.half=1;f.leftScore=finalHostGoals;f.rightScore=finalGuestGoals;}
        f.hudEvent=hudEvent;f.hudSerial=hudSerial;
        f.hostIndex=teamIndex(teams[0]);
        SelectionDest selection=m.cSpecialBallSel;
        if(selection!=null){
            f.selectionVisible=selection.m_bVisible&&selection.m_cPointer!=null;
            f.selectionTeam=selection.m_cTeam==teams[0]?0:selection.m_cTeam==teams[1]?1:-1;
            Vector p=selection.GetPosition();f.selectionPosition=new float[]{p.fX,p.fY,p.fZ};
        }
        int n=2;for(int t=0;t<2;t++){Team team=teams[t];f.count[t]=team.GetFootBallerCount();n+=f.count[t];
            f.side[t]=team.m_nSide;f.focus[t]=index(team,team.m_cFocusFBaller);f.active[t]=index(team,team.m_cActiveFootBaller);}
        f.actors=new CXOnlineState.Actor[n];int i=0;
        for(int t=0;t<2;t++)for(int j=0;j<f.count[t];j++)f.actors[i++]=actor(teams[t].GetFootBaller(j));
        f.actors[i++]=actor(GameField.m_cBall);f.actors[i]=actor(m.GetReferee());return f;
    }
    private static void freeze(ControlObject object){
        if(object==null)return;object.ClearDestinationPos();object.ClearDestinationDir();
        // Ball.SetSpeed explicitly reactivates native physics. Disable it last.
        object.SetSpeed(new Vector(0,0,0));object.SetPhysicsActive(false);
    }
    private static void freezeActors(AIMatch m){
        for(int t=0;t<2;t++)for(int j=0;j<m.GetTeam(t).GetFootBallerCount();j++)freeze(m.GetTeam(t).GetFootBaller(j));
        freeze(GameField.m_cBall);freeze(m.GetReferee());
    }
    private static void hold(ControlObject object){
        if(object==null)return;
        if(!heldPhysics.containsKey(object))heldPhysics.put(object,object.GetPhysicsActive()?Boolean.TRUE:Boolean.FALSE);
        object.SetPhysicsActive(false);
    }
    private static void holdActors(AIMatch m){
        for(int t=0;t<2;t++)for(int j=0;j<m.GetTeam(t).GetFootBallerCount();j++)hold(m.GetTeam(t).GetFootBaller(j));
        hold(GameField.m_cBall);hold(m.GetReferee());
    }
    private static void releaseHeldActors(){
        java.util.Enumeration objects=heldPhysics.keys();
        while(objects.hasMoreElements()){ControlObject object=(ControlObject)objects.nextElement();
            object.SetPhysicsActive(((Boolean)heldPhysics.get(object)).booleanValue());}
        heldPhysics.clear();
    }
    private static void applyActor(ControlObject object,CXOnlineState.Actor a) {
        float[] v=a.transform;freeze(object);
        if(object.GetParent()!=null)object.DetachFromParentAndKeepWorldPos();
        object.FromUpForwardPos(new Vector(v[6],v[7],v[8]),new Vector(v[3],v[4],v[5]),new Vector(v[0],v[1],v[2]));
        if(object instanceof FootBaller && a.animation.length()>0){
            Integer old=(Integer)animations.get(object);
            if(old==null||old.intValue()!=a.animationSerial){((FootBaller)object).PlayAnim(a.animation,a.animationFlags);animations.put(object,new Integer(a.animationSerial));}
        }
    }
    private static void applySnapshot(CXOnlineState.Frame f) throws IOException {
        AIMatch m=SoccerModule.m_cMatch;
        for(int t=0;t<2;t++)if(f.count[t]!=teams[t].GetFootBallerCount())throw new IOException("Team mismatch");
        boolean sideChanged=m.GetTeam(f.hostIndex)!=teams[0];
        m.m_teams[f.hostIndex]=teams[0];m.m_teams[1-f.hostIndex]=teams[1];
        int i=0;for(int t=0;t<2;t++)for(int j=0;j<f.count[t];j++){
            FootBaller fb=teams[t].GetFootBaller(j);fb.m_nTeam=t==0?f.hostIndex:1-f.hostIndex;
            applyActor(fb,f.actors[i++]);
        }
        applyActor(GameField.m_cBall,f.actors[i++]);applyActor(m.GetReferee(),f.actors[i]);
        m.m_nScoreLeft=f.leftScore;m.m_nScoreRight=f.rightScore;m.m_nHalfNo=f.half;
        // Assign only the replicated state value; do not dispatch guest state transitions.
        AIMatch.m_nMatchState=f.state;Match.m_bPlaying=f.playing;module.m_Clock.m_fTime=f.clock;module.m_Clock.m_bStop=true;
        for(int t=0;t<2;t++){Team team=teams[t];team.m_nSide=f.side[t];
            team.m_cFocusFBaller=f.focus[t]<0?null:team.GetFootBaller(f.focus[t]);
            team.m_cActiveFootBaller=f.active[t]<0?null:team.GetFootBaller(f.active[t]);
            for(int j=0;j<f.count[t];j++){
                FootBaller fb=team.GetFootBaller(j);boolean focused=fb==team.m_cFocusFBaller;
                boolean focusChanged=appliedSequence<0||fb.bInputFocus!=focused;
                fb.DisableCallMethod("DelayFocus");fb.bInputFocus=focused;
                if(focusChanged&&fb.cSelectionObj!=null){if(focused)fb.cSelectionObj.Show();else fb.cSelectionObj.Hide();}
            }
        }
        SelectionDest selection=m.cSpecialBallSel;
        if(selection!=null){
            selection.m_bActive=false;selection.SetPhysicsActive(false);selection.SetSpeed(new Vector(0,0,0));
            selection.m_cTeam=f.selectionTeam<0?null:(AITeam)teams[f.selectionTeam];
            if(selection.m_cPointer!=null){
                if(f.selectionVisible){selection.SetPositionWorld(new Vector(f.selectionPosition[0],f.selectionPosition[1],f.selectionPosition[2]));selection.Show();}
                else selection.Hide();
            }
        }
        syncPlayerTeams();
        if(sideChanged)module.GetSoccerCamera().ChangeMode(module.GetSoccerCamera().m_nMode);
        FootBaller focus=teams[1].m_cFocusFBaller;
        module.GetSoccerCamera().SetObserved(focus==null?(ControlObject)GameField.m_cBall:focus);
        module.GetSoccerCamera().UnFreeze();
        if(SoccerModule.m_cHud!=null){SoccerModule.m_cHud.UpdateScore(f.leftScore,f.rightScore);
            SoccerModule.m_cHud.UpdateClock(module.m_Clock.GetMatchTime(),false);
            if(f.hudSerial>appliedHudSerial&&f.hudEvent>=0){SoccerModule.m_cHud.ShowEventInfo(f.hudEvent);appliedHudSerial=f.hudSerial;}
            for(int t=0;t<2;t++)for(int j=0;j<f.count[t];j++)SoccerModule.m_cHud.UpdateFBPosition(teams[t].GetFootBaller(j));
            SoccerModule.m_cHud.UpdateBallPosition(GameField.m_cBall);}
        appliedSequence=f.sequence;lastReceived=System.currentTimeMillis();snapshotsApplied++;status="Online 1v1";
        if(f.finished&&!finished){finished=true;finalHostGoals=f.leftScore;finalGuestGoals=f.rightScore;status="Match completed";}
        if(finished)flushCompletion();
    }
}
