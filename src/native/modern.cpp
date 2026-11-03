// Included into the JNI bridge so all graphics/input changes run on the game thread.
#include "gothic_audio.h"
#include <vector>
#include <string>
static int remaster=1,vsync=1,fps=60,hudOn=1,voiceOn=1,subsOn=1,invertY=0,autoPause=0,cameraFov=0;
static bool graphicsDirty=true,uiReady=false,wasForeground=true;
static DWORD subtitleUntil=0,lastHud=0,lastEvent=0;static const char* subtitle="";
static jclass uw,us,ui,sp,ph,td,ind,fb,cxHudCore;
static jmethodID cxHudWidgetFont;
static jstring cxHudFontName=nullptr,cxHudLookupNames[5]={};
static jmethodID getElem,setText,setVisible,setTexture,showUI,hideUI,getName,loadUI,createObj,loadfontNative;
static jfieldID uiId,uiModule,playerTeamField,numberField,teamLeftField,teamRightField,logoField;
static jobject modernOptions=nullptr,previousOptions=nullptr;
static std::vector<jobject> closedOptions;
static bool recoveryInGamePending=false;
static GLuint nextTexture=1;static float maxAniso=1;
static DWORD cxTextureScanAfter=0;static jobject cxGraphicsModule=nullptr;
extern "C" JNIEXPORT void JNICALL Java_CXSupport_TexturesChanged(JNIEnv*,jclass){nextTexture=1;cxTextureScanAfter=GetTickCount()+400;}

static void writeInt(const char* sec,const char* name,int value){char v[20];sprintf_s(v,"%d",value);WritePrivateProfileStringA(sec,name,v,ini);}
static int readInt(const char* sec,const char* key,int def){return (int)GetPrivateProfileIntA(sec,key,def,ini);}
static void modernInit(){remaster=readInt("Graphics","Remaster",1)!=0;vsync=readInt("Graphics","VSync",1)!=0;fps=std::clamp(readInt("Graphics","FPSLimit",60),0,240);hudOn=readInt("Interface","PlayerPanels",1)!=0;voiceOn=readInt("Audio","GothicCommentary",1)!=0;subsOn=readInt("Audio","Subtitles",1)!=0;invertY=readInt("Gamepad","InvertCursorY",0)!=0;autoPause=readInt("Gameplay","PauseOnFocusLoss",0)!=0;cameraFov=readInt("Graphics","CameraFOV",0);}
static int getPlayerTeam(JNIEnv* e,jobject match,int player){
 if(!playerTeamField)playerTeamField=e->GetFieldID(mt,"m_nPlayer1Team","I");int p=e->GetIntField(match,playerTeamField);p=(p==1)?1:0;return player?1-p:p;
}
static bool cxHudInitStrings(JNIEnv* e){
 if(cxHudFontName)return true;
 // Commit all six process-lifetime roots together; failure leaves an empty cache.
 static const char* ids[]={"CX_NAME_LEFT","CX_NAME_RIGHT","CX_BADGE_LEFT","CX_BADGE_RIGHT","CX_SUBTITLE","CXHud"};
 jstring created[6]={};
 auto fail=[&](){for(jstring name:created)if(name)e->DeleteGlobalRef(name);error(e,"HUD lookup strings");return false;};
 for(int i=0;i<6;i++){
  jstring local=e->NewStringUTF(ids[i]);if(!local)return fail();
  created[i]=(jstring)e->NewGlobalRef(local);e->DeleteLocalRef(local);if(!created[i])return fail();
 }
 for(int i=0;i<5;i++)cxHudLookupNames[i]=created[i];cxHudFontName=created[5];return true;
}
static bool uiAPI(JNIEnv* e){
 if(uiReady)return true;
 uw=cls(e,"UIWindow");us=cls(e,"UIStatic");ui=cls(e,"UserInterface");sp=cls(e,"Sprite");ph=cls(e,"PetSoccerHud");td=cls(e,"TeamData");ind=cls(e,"Individual");fb=cls(e,"FootBaller");if(!cxHudCore)cxHudCore=cls(e,"CoreLogic");
 if(error(e,"UI classes"))return false;
 getElem=e->GetMethodID(uw,"GetElem","(Ljava/lang/String;)LUIWindow;");setText=e->GetMethodID(us,"SetText","(Ljava/lang/String;)V");setVisible=e->GetMethodID(uw,"SetVisible","(Z)V");setTexture=e->GetMethodID(uw,"SetTexture","(LUITexture;)V");showUI=e->GetMethodID(ui,"Show","()V");hideUI=e->GetMethodID(ui,"Hide","()V");getName=e->GetMethodID(ind,"GetIndividualName","()Ljava/lang/String;");loadUI=e->GetMethodID(ui,"Load","(LModule;Ljava/lang/String;Z)Z");createObj=e->GetMethodID(go,"CreateObject","(Ljava/lang/String;)LGameObject;");loadfontNative=e->GetMethodID(go,"LoadFont","(Ljava/lang/String;Ljava/lang/String;I)Z");
 uiId=e->GetFieldID(uw,"m_sId","Ljava/lang/String;");uiModule=e->GetFieldID(uw,"m_module","LModule;");numberField=e->GetFieldID(fb,"m_nNumberInTeam","I");teamLeftField=e->GetStaticFieldID(cxHudCore,"m_cTeamDataLeft","LTeamData;");teamRightField=e->GetStaticFieldID(cxHudCore,"m_cTeamDataRight","LTeamData;");logoField=e->GetFieldID(td,"m_cLogo","LUITexture;");
 cxHudWidgetFont=e->GetMethodID(sp,"SetFont","(Ljava/lang/String;)Z");
 if(error(e,"UI members")||!cxHudInitStrings(e))return false;uiReady=true;return true;
}
static jobject elem(JNIEnv* e,jobject root,const char* id){jstring s=e->NewStringUTF(id);jobject o=e->CallObjectMethod(root,getElem,s);e->DeleteLocalRef(s);return o;}
static jobject cxHudElem(JNIEnv* e,jobject root,int index){return e->CallObjectMethod(root,getElem,cxHudLookupNames[index]);}
#include "hud_cache.h"
static void text(JNIEnv* e,jobject root,const char* id,const char* value){jobject o=elem(e,root,id);if(o){jstring s=e->NewStringUTF(value);e->CallVoidMethod(o,setText,s);e->DeleteLocalRef(s);e->DeleteLocalRef(o);}}
static void label(JNIEnv* e,jobject root,const char* id,const char* caption,int value,bool yesno=true){char b[150];if(yesno)sprintf_s(b,"%s: %s",caption,value?"WL.":"WYL.");else sprintf_s(b,"%s: %d",caption,value);text(e,root,id,b);}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_RefreshOptions(JNIEnv* e,jclass,jobject root){
 if(!uiAPI(e))return;label(e,root,"CX_EXTRA_TEAMS","Dodatkowe kluby",readInt("Content","ExtraTeams",0)!=0);label(e,root,"CX_REMASTER","Remaster",remaster);text(e,root,"CX_DISPLAY_NOTICE",displayNotice);label(e,root,"CX_RM","Remaster / filtrowanie 16x",remaster);label(e,root,"CX_VSYNC","Synchronizacja pionowa",vsync);
 if(fps)label(e,root,"CX_FPS","Limit FPS",fps,false);else text(e,root,"CX_FPS","Limit FPS: bez limitu");
 label(e,root,"CX_HUD","Panele zawodnikow",hudOn);label(e,root,"CX_VOICE","Komentarz Gothic",voiceOn);label(e,root,"CX_PAD","Dwa pady XInput",enabled);label(e,root,"CX_DEADZONE","Martwa strefa (%)",leftDZ*100/32767,false);label(e,root,"CX_CURSOR","Predkosc kursora",cursorSpeed,false);label(e,root,"CX_INVERT","Odwroc os Y kursora",invertY);label(e,root,"CX_PAUSE","Pauza po utracie fokusu",autoPause);
 if(cameraFov)label(e,root,"CX_CAMERA","Kat widzenia kamery",cameraFov,false);else text(e,root,"CX_CAMERA","Kamera: oryginalna");label(e,root,"CX_P1","Pad gracza 1 (port 1-4)",ports[0]+1,false);label(e,root,"CX_P2","Pad gracza 2 (port 1-4)",ports[1]+1,false);error(e,"refresh settings");
}
// CXOptions owns its complete, synchronous tree/focus/stacking lifecycle.
// Keep destruction deferred until the native UI command has returned.
static bool queueOptionsDisposal(JNIEnv* e,jobject panel){
 if(!panel)return false;jobject held=e->NewGlobalRef(panel);
 if(!held){if(e->ExceptionCheck())e->ExceptionClear();logf("OPTIONS could not retain disposal reference");return false;}
 closedOptions.push_back(held);return true;
}
static bool optionsException(JNIEnv* e,const char* stage){
 if(!e->ExceptionCheck())return false;
 e->ExceptionDescribe();e->ExceptionClear();logf("OPTIONS failure: %s; keeping parent usable",stage);return true;
}
static void openOptions(JNIEnv* e,jobject parent){
 if(!uiAPI(e)||modernOptions||!parent)return;
 jobject module=e->GetObjectField(parent,uiModule);if(!module)return;
 jstring name=e->NewStringUTF("CXOptions");jobject o=e->CallObjectMethod(module,createObj,name);e->DeleteLocalRef(name);
 if(optionsException(e,"create")||!o)return;
 for(auto spec:{std::pair<const char*,float>("CXUI",.029f),{"CXTitle",.04f}}){
  jstring id=e->NewStringUTF(spec.first),face=e->NewStringUTF("FL Romanski 13");int h=e->CallStaticIntMethod(go,screenH);
  jboolean fontOK=e->CallBooleanMethod(module,loadfontNative,id,face,(int)(h*spec.second));
  if(!fontOK)logf("OPTIONS font registration returned false: %s (existing alias may remain)",spec.first);
  e->DeleteLocalRef(id);e->DeleteLocalRef(face);
 }
 if(optionsException(e,"fonts")){queueOptionsDisposal(e,o);return;}
 name=e->NewStringUTF("data/menu/scr/CXOptions.scr");jboolean loaded=e->CallBooleanMethod(o,loadUI,module,name,JNI_FALSE);e->DeleteLocalRef(name);
 if(optionsException(e,"load")||!loaded){queueOptionsDisposal(e,o);return;}
 jobject back=elem(e,o,"CX_BACK"),teams=elem(e,o,"CX_EXTRA_TEAMS"),title=elem(e,o,"CX_TITLE");
 logf("OPTIONS controls found: back=%d teams=%d title=%d",back!=nullptr,teams!=nullptr,title!=nullptr);
 bool complete=back&&teams&&title;
 if(complete){
  // Validate the aliases on real sprites, including when LoadFont returned
  // false because an alias was already present from an earlier opening.
  jstring bodyFont=e->NewStringUTF("CXUI"),titleFont=e->NewStringUTF("CXTitle");
  jboolean backFont=e->CallBooleanMethod(back,cxHudWidgetFont,bodyFont),teamsFont=e->CallBooleanMethod(teams,cxHudWidgetFont,bodyFont),headingFont=e->CallBooleanMethod(title,cxHudWidgetFont,titleFont);
  logf("OPTIONS font binding: back=%d teams=%d title=%d",backFont,teamsFont,headingFont);
  complete=backFont&&teamsFont&&headingFont;
  e->DeleteLocalRef(bodyFont);e->DeleteLocalRef(titleFont);
 }
 if(back)e->DeleteLocalRef(back);if(teams)e->DeleteLocalRef(teams);if(title)e->DeleteLocalRef(title);
 if(optionsException(e,"required controls")||!complete){logf("OPTIONS missing Back or Additional Clubs; parent remains visible");queueOptionsDisposal(e,o);return;}
 Java_CXSupport_RefreshOptions(e,nullptr,o);
 if(optionsException(e,"refresh")||disabled){logf("OPTIONS refresh failed; parent remains usable");queueOptionsDisposal(e,o);return;}
 jclass options=e->GetObjectClass(o);jmethodID open=e->GetMethodID(options,"Open","(LUserInterface;)Z");
 if(optionsException(e,"Open lookup")||!open){e->DeleteLocalRef(options);queueOptionsDisposal(e,o);return;}
 jobject heldPanel=e->NewGlobalRef(o),heldParent=e->NewGlobalRef(parent);
 if(optionsException(e,"retain panel/parent")||!heldPanel||!heldParent){
  if(heldPanel)e->DeleteGlobalRef(heldPanel);if(heldParent)e->DeleteGlobalRef(heldParent);
  e->DeleteLocalRef(options);queueOptionsDisposal(e,o);return;
 }
 jboolean shown=e->CallBooleanMethod(o,open,parent);
 if(optionsException(e,"Open")||!shown){
  jmethodID rollback=e->GetMethodID(options,"CloseToParent","()V");
  bool rollbackFailed=optionsException(e,"rollback lookup")||!rollback;
  if(!rollbackFailed){e->CallVoidMethod(o,rollback);rollbackFailed=optionsException(e,"rollback");}
  e->DeleteLocalRef(options);
  if(rollbackFailed){
   modernOptions=heldPanel;previousOptions=heldParent;e->CallVoidMethod(o,showUI);optionsException(e,"Open recovery modal");
   logf("OPTIONS open/restore failed; snapshot/modal retained for recovery");return;
  }
  e->DeleteGlobalRef(heldPanel);e->DeleteGlobalRef(heldParent);queueOptionsDisposal(e,o);return;
 }
 e->DeleteLocalRef(options);
 modernOptions=heldPanel;previousOptions=heldParent;
 logf("modern settings opened: complete controls/tree raised, parent input suspended");
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_CloseOptions(JNIEnv* e,jclass){
 if(!modernOptions)return;
 jclass options=e->GetObjectClass(modernOptions);jmethodID close=e->GetMethodID(options,"CloseToParent","()V");
 bool failed=optionsException(e,"Close lookup")||!close;
 if(!failed){e->CallVoidMethod(modernOptions,close);failed=optionsException(e,"Close");}
 e->DeleteLocalRef(options);
 if(failed){
  // Retain the Java snapshot and a usable modal; a root-only parent Show
  // cannot safely reconstruct conditionally hidden children after a failure.
  e->CallVoidMethod(modernOptions,showUI);optionsException(e,"Close retry modal");
  logf("OPTIONS parent restore incomplete; modal retained for retry");return;
 }
 queueOptionsDisposal(e,modernOptions);e->DeleteGlobalRef(modernOptions);modernOptions=nullptr;
 if(previousOptions){e->DeleteGlobalRef(previousOptions);previousOptions=nullptr;}
 logf("modern settings closed: parent restored, disposal queued");
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_HandleVideoKey(JNIEnv* e,jclass,jint code,jboolean down){
 if(code!=67||!down)return JNI_FALSE; // F9, independent of mouse position.
 if(!initAPI(e))return JNI_TRUE;
 if(modernOptions)Java_CXSupport_CloseOptions(e,nullptr);
 jobject settings=e->GetStaticObjectField(sg,settingsField);if(!settings)return JNI_TRUE;
 displayFullscreen=0;e->SetIntField(settings,resField,2);firstApply=false;
 e->CallVoidMethod(settings,e->GetMethodID(gs,"SetCurrentSettings","()V"));
 jobject game=e->GetStaticObjectField(sg,gameField),module=e->GetStaticObjectField(sg,moduleField);
 if(game&&module&&e->GetIntField(game,activeField)==2)recoveryInGamePending=true;
 else{jobject menu=e->GetStaticObjectField(sg,e->GetStaticFieldID(sg,"firstMenuModule","LSoccerMainMenuModule;"));if(menu){jstring changed=e->NewStringUTF("OnChangeResolution");e->CallVoidMethod(menu,e->GetMethodID(go,"CallMethodIn","(Ljava/lang/String;F)V"),changed,0.f);}}
 sprintf_s(displayNotice,"F9: bezpieczny ekran\n1024x768 w oknie.");logf("VIDEO RECOVERY F9 1024x768 window");error(e,"F9 video recovery");return JNI_TRUE;
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_HandleUI(JNIEnv* e,jclass,jobject root,jobject control,jint command){
 if((command!=0&&command!=2)||!control||!uiAPI(e))return JNI_FALSE;jstring id=(jstring)e->GetObjectField(control,uiId);if(!id)return JNI_FALSE;const char* raw=e->GetStringUTFChars(id,nullptr);char s[90];strncpy_s(s,raw,_TRUNCATE);e->ReleaseStringUTFChars(id,raw);e->DeleteLocalRef(id);
 if(strncmp(s,"CX_",3))return JNI_FALSE;
 if(!strcmp(s,"CX_MODERN")){openOptions(e,root);return JNI_TRUE;}if(!strcmp(s,"CX_BACK")){Java_CXSupport_CloseOptions(e,nullptr);return JNI_TRUE;}
 if(!strcmp(s,"CX_RM")||!strcmp(s,"CX_REMASTER")){remaster=!remaster;writeInt("Graphics","Remaster",remaster);graphicsDirty=true;nextTexture=1;}
 else if(!strcmp(s,"CX_VSYNC")){vsync=!vsync;writeInt("Graphics","VSync",vsync);graphicsDirty=true;}
 else if(!strcmp(s,"CX_FPS")){const int values[]={0,30,60,120,144,165,240};int n=0;for(int i=0;i<7;i++)if(values[i]==fps)n=(i+1)%7;fps=values[n];writeInt("Graphics","FPSLimit",fps);}
 else if(!strcmp(s,"CX_HUD")){hudOn=!hudOn;writeInt("Interface","PlayerPanels",hudOn);}
 else if(!strcmp(s,"CX_VOICE")){voiceOn=!voiceOn;writeInt("Audio","GothicCommentary",voiceOn);}
 else if(!strcmp(s,"CX_EXTRA_TEAMS")){writeInt("Content","ExtraTeams",readInt("Content","ExtraTeams",0)==0);}
 else if(!strcmp(s,"CX_SUBS")){subsOn=!subsOn;writeInt("Audio","Subtitles",subsOn);}
 else if(!strcmp(s,"CX_PAD")){enabled=!enabled;writeInt("Gamepad","Enabled",enabled);}
 else if(!strcmp(s,"CX_DEADZONE")){int pct=leftDZ*100/32767;pct=pct<14?15:pct<19?20:pct<24?25:pct<29?30:10;leftDZ=pct*32767/100;writeInt("Gamepad","LeftDeadzone",leftDZ);}
 else if(!strcmp(s,"CX_CURSOR")){cursorSpeed=cursorSpeed>=1500?300:cursorSpeed+300;writeInt("Gamepad","CursorSpeed",cursorSpeed);}
 else if(!strcmp(s,"CX_INVERT")){invertY=!invertY;writeInt("Gamepad","InvertCursorY",invertY);}
 else if(!strcmp(s,"CX_PAUSE")){autoPause=!autoPause;writeInt("Gameplay","PauseOnFocusLoss",autoPause);}
 else if(!strcmp(s,"CX_CAMERA")){cameraFov=cameraFov==0?70:cameraFov==70?80:cameraFov==80?90:0;writeInt("Graphics","CameraFOV",cameraFov);}
 else if(!strcmp(s,"CX_P1")||!strcmp(s,"CX_P2")){int n=!strcmp(s,"CX_P2");ports[n]=(ports[n]+1)%4;if(ports[n]==ports[1-n])ports[1-n]=(ports[n]+1)%4;for(int i=0;i<2;i++){writeInt("Gamepad",i?"Player2":"Player1",ports[i]);release(e,players[i]);}padSaveModernPorts(e);}
 Java_CXSupport_RefreshOptions(e,nullptr,root);return JNI_TRUE;
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_UpdateHud(JNIEnv* e,jclass,jobject hud){
 DWORD now=GetTickCount();if(now-lastHud<80||!uiAPI(e))return;lastHud=now;jobject match=e->GetStaticObjectField(sm,matchField);jobject module=e->GetStaticObjectField(sg,moduleField);bool menu=module&&e->GetBooleanField(module,menuField);
 static int fontHeight=0;static unsigned fontEpoch=0;
 int currentHeight=e->CallStaticIntMethod(go,screenH);
 jstring hudFont=cxHudFontName;
 if(fontHeight!=currentHeight||fontEpoch!=reviewGraphicsEpoch){jstring face=e->NewStringUTF("FL Romanski 13");e->CallBooleanMethod(hud,loadfontNative,hudFont,face,(jint)std::max(14,currentHeight*24/1000));e->DeleteLocalRef(face);fontHeight=currentHeight;fontEpoch=reviewGraphicsEpoch;}
 jmethodID widgetFont=cxHudWidgetFont;
 for(int i=0;i<2;i++){
  jobject team=match?e->CallObjectMethod(match,getTeam,getPlayerTeam(e,match,i)):nullptr;jobject focus=team?e->GetObjectField(team,focusField):nullptr;bool visible=hudOn&&!menu&&team&&focus&&e->GetBooleanField(team,userField);
  jobject panel=cxHudElem(e,hud,i),badge=cxHudElem(e,hud,i+2);
 if(panel){cxHudFont(e,panel,i,hudFont,currentHeight,widgetFont);cxHudVisible(e,panel,i,visible);if(visible){jstring nm=(jstring)e->CallObjectMethod(focus,getName);if(nm){const jchar* name=e->GetStringChars(nm,nullptr);std::wstring shortName((const wchar_t*)name,e->GetStringLength(nm));auto first=shortName.find(L'"'),last=shortName.rfind(L'"');if(first!=std::wstring::npos&&last>first+1)shortName=shortName.substr(first+1,last-first-1);if(shortName.size()>22){auto space=shortName.rfind(L' ');if(space!=std::wstring::npos)shortName=shortName.substr(0,1)+L". "+shortName.substr(space+1);}if(shortName.size()>22)shortName=shortName.substr(0,21)+L"\u2026";int number=e->GetIntField(focus,numberField)+1;wchar_t value[150];swprintf_s(value,L"%d  %s",number,shortName.c_str());cxHudText(e,panel,i,value);e->ReleaseStringChars(nm,name);e->DeleteLocalRef(nm);}}}
  if(badge){cxHudVisible(e,badge,i+2,visible);if(visible){int ti=getPlayerTeam(e,match,i);jobject data=e->GetStaticObjectField(cxHudCore,ti?teamRightField:teamLeftField);if(data){jobject logo=e->GetObjectField(data,logoField);if(logo)reviewSetBadge(e,badge,logo,i);}}}
 }
 jobject sub=cxHudElem(e,hud,4);if(sub)e->CallVoidMethod(sub,setVisible,JNI_FALSE);
 cxUpdateGothicHud(e,hud,menu);
 error(e,"HUD player labels");
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_CommentEvent(JNIEnv* e,jclass,jobject commentator,jint event){
 if(!voiceOn||event<0||event>3||disabled)return JNI_FALSE;DWORD now=GetTickCount();if(event!=0&&now-lastEvent<500)return JNI_TRUE;
 jclass c=e->GetObjectClass(commentator);jmethodID isActive=e->GetMethodID(c,"IsActive","()Z");if(!e->CallBooleanMethod(commentator,isActive))return JNI_TRUE;
 e->CallVoidMethod(commentator,e->GetMethodID(c,"ClearCurrComment","()V"));e->SetIntField(commentator,e->GetFieldID(c,"m_nCurrComment","I"),event==0?4:event==1?20:event==2?19:5);
 int variant=(now/17)%voiceCounts[event];jstring path=e->NewStringUTF(voicePaths[event][variant]);float duration=e->CallFloatMethod(commentator,e->GetMethodID(c,"Say","(Ljava/lang/String;)F"),path);jstring stop=e->NewStringUTF("StopTalking");e->CallVoidMethod(commentator,e->GetMethodID(go,"CallMethodIn","(Ljava/lang/String;F)V"),stop,duration);
 subtitle="";subtitleUntil=0;cxStartGothicQuote(e,commentator,event,variant,duration);lastEvent=now;logf("GOTHIC event=%d file=%s duration=%.2f",event,voicePaths[event][variant],duration);error(e,"Gothic commentary");return JNI_TRUE;
}
static void modernFrame(JNIEnv* e,jobject game,jobject module,bool inGame,bool menus){
 if(recoveryInGamePending&&module&&inGame&&uiAPI(e)){
  recoveryInGamePending=false;
  logf("RECOVERY STEP fonts lookup");jclass moduleClass=e->FindClass("Module"),fontClass=e->FindClass("SoccerFonts");
  jobject fonts=e->GetStaticObjectField(moduleClass,e->GetStaticFieldID(moduleClass,"fonts","LFonts;"));
  int logical=e->CallStaticIntMethod(sg,e->GetStaticMethodID(sg,"GetResolution","()I"));
  if(fonts)e->CallVoidMethod(fonts,e->GetMethodID(fontClass,"LoadFonts","(I)V"),logical);
  logf("RECOVERY STEP fonts loaded");int width=e->CallStaticIntMethod(go,screenW),height=e->CallStaticIntMethod(go,screenH);
  jintArray ids=(jintArray)e->GetStaticObjectField(sm,e->GetStaticFieldID(sm,"m_CamsIDs","[I"));
  jmethodID origin=e->GetMethodID(moduleClass,"SetViewOrigin","(IFF)V"),size=e->GetMethodID(moduleClass,"SetViewSize","(IFF)V");
  if(ids)for(int i=0;i<std::min(1,(int)e->GetArrayLength(ids));i++){jint id;e->GetIntArrayRegion(ids,i,1,&id);if(id>=0){logf("RECOVERY STEP view id=%d",id);e->CallVoidMethod(module,origin,id,0.f,0.f);e->CallVoidMethod(module,size,id,1.f,1.f);}}
  logf("RECOVERY STEP views updated");jmethodID reflow=e->GetMethodID(ui,"OnChangeResolution","()V");
  jobject hud=e->GetStaticObjectField(sm,e->GetStaticFieldID(sm,"m_cHud","LPetSoccerHud;"));if(hud)e->CallVoidMethod(hud,reflow);
  logf("RECOVERY STEP HUD updated");jclass pauseClass=e->FindClass("SoccerInGameMenuModule");jobject pause=e->GetObjectField(module,e->GetFieldID(sm,"m_cMenuInGameModule","LSoccerInGameMenuModule;"));
  if(pause)for(auto item:{std::pair<const char*,const char*>("m_cMenuInGame","LMenuInGame;"),{"m_cMenuYesNo","LMenuYesNoDialog;"}}){jobject root=e->GetObjectField(pause,e->GetFieldID(pauseClass,item.first,item.second));if(root)e->CallVoidMethod(root,reflow);}
  logf("VIDEO RECOVERY active game view and HUD resized %dx%d",width,height);error(e,"active game video recovery");
 }
 for(jobject closed:closedOptions){
  jobject owner=e->GetObjectField(closed,uiModule);
  e->CallVoidMethod(closed,e->GetMethodID(uw,"ReleaseTextures","()V"));
  e->CallVoidMethod(closed,e->GetMethodID(ui,"Remove","()V"));
  if(owner)e->CallVoidMethod(owner,e->GetMethodID(go,"RemoveSprite","(LSprite;)V"),closed);
  e->CallVoidMethod(closed,e->GetMethodID(go,"delete","()V"));e->DeleteGlobalRef(closed);
  logf("modern settings disposed after close");
 }
 closedOptions.clear();
 static LARGE_INTEGER last={},freq={};if(!freq.QuadPart)QueryPerformanceFrequency(&freq);if(fps>0&&foreground()){LARGE_INTEGER n;QueryPerformanceCounter(&n);if(last.QuadPart){double ms=(n.QuadPart-last.QuadPart)*1000.0/freq.QuadPart;double wait=1000.0/fps-ms;if(wait>=1)Sleep((DWORD)wait);}QueryPerformanceCounter(&last);}else last.QuadPart=0;
 reviewObserveContext(wglGetCurrentContext());
 if((module&&!cxGraphicsModule)||(!module&&cxGraphicsModule)||(module&&cxGraphicsModule&&!e->IsSameObject(module,cxGraphicsModule))){cxResetGothicQuote(e);if(cxGraphicsModule)e->DeleteGlobalRef(cxGraphicsModule);cxGraphicsModule=module?e->NewGlobalRef(module):nullptr;Java_CXSupport_TexturesChanged(e,nullptr);}
 if(wglGetCurrentContext()){
  if(graphicsDirty){auto swap=(BOOL(WINAPI*)(int))wglGetProcAddress("wglSwapIntervalEXT");INT_PTR swapAddress=(INT_PTR)swap;if(swapAddress!=0&&swapAddress!=1&&swapAddress!=2&&swapAddress!=3&&swapAddress!=-1)swap(vsync);const char* ex=(const char*)glGetString(GL_EXTENSIONS);if(ex&&strstr(ex,"GL_EXT_texture_filter_anisotropic")){glGetFloatv(0x84ff,&maxAniso);maxAniso=std::min(maxAniso,16.f);}graphicsDirty=false;logf("GRAPHICS remaster=%d anisotropy=%.0f vsync=%d fps=%d",remaster,maxAniso,vsync,fps);}
  if(maxAniso>1&&nextTexture<65536&&(LONG)(GetTickCount()-cxTextureScanAfter)>=0){GLint bound=0;glGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);for(int i=0;i<64&&nextTexture<65536;i++,nextTexture++){if(glIsTexture(nextTexture)){glBindTexture(GL_TEXTURE_2D,nextTexture);glTexParameterf(GL_TEXTURE_2D,0x84fe,remaster?maxAniso:1.f);}}glBindTexture(GL_TEXTURE_2D,bound);}
 }
 bool fg=foreground();if(autoPause&&wasForeground&&!fg&&inGame&&!menus&&module)e->CallVoidMethod(module,e->GetMethodID(sm,"ShowMenu","()V"));wasForeground=fg;
 if(inGame&&module)reviewApplyCamera(e,module);
 cxAnimateGothicQuote(e,inGame&&!menus);
}
