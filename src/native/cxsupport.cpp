#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <Xinput.h>
#include <tlhelp32.h>
#include <jni.h>
#include <gl/GL.h>
#include <cstdio>
#include <cstdarg>
#include <cmath>
#include <algorithm>

// A 32-bit JNI bridge. Gameplay uses the game's own InputAction classes.
static char ini[MAX_PATH],logpath[MAX_PATH];
static char displayNotice[160]="";
static int preset=3,enabled=1,ports[2]={0,1},leftDZ=7849,rightDZ=8689,cursorSpeed=900;
static int displayFullscreen=-1;
#include "bitmap_font_aliases.h"
static bool initialized=false,firstApply=true,apiReady=false,disabled=false,mouseDown=false;
static DWORD lastTick=0,mapperCheck=0;static bool mapper=false;
static HMODULE xi;static DWORD (WINAPI *getState)(DWORD,XINPUT_STATE*);
static jclass sg,go,gs,sm,mt,tm,tc,analog,digital;
static jfieldID gameField,settingsField,resField,activeField,moduleField,matchField,menuField,pauseField,userField,ctrlField,focusField,keyField,tcTeamField;
static jmethodID setRes,setFull,apply,screenW,screenH,loadFont,getTeam,analogCtor,digitalCtor,analogMove,digitalButton;
struct Player { jobject ctrl=nullptr,move=nullptr,special=nullptr,buttons[4]={}; WORD previous=0;bool connected=false;int mask=0;};
static Player players[2];static unsigned frameCount=0;static unsigned reviewGraphicsEpoch=0;
static void modernInit();static void modernFrame(JNIEnv*,jobject,jobject,bool,bool);
static int getPlayerTeam(JNIEnv*,jobject,int);
static int padControllerPort(JNIEnv*,jobject);
static void padSaveModernPorts(JNIEnv*);
static bool padCursorInverted();
static void reviewReleaseInjectedInput();
static void reviewCommitInjectedInput(bool,bool,bool,bool);
static void reviewGraphicsChanged();
static void reviewObserveContext(HGLRC);
static void reviewSetBadge(JNIEnv*,jobject,jobject,int);
static void reviewApplyCamera(JNIEnv*,jobject);
static void cxStartGothicQuote(JNIEnv*,jobject,int,int,float);
static void cxUpdateGothicHud(JNIEnv*,jobject,bool);
static void cxAnimateGothicQuote(JNIEnv*,bool);
static void cxResetGothicQuote(JNIEnv*);

static void logf(const char* fmt,...) {FILE* f=nullptr;fopen_s(&f,logpath,"a");if(!f)return;fprintf(f,"%lu ",GetTickCount());va_list a;va_start(a,fmt);vfprintf(f,fmt,a);va_end(a);fputc('\n',f);fclose(f);}
static bool error(JNIEnv* e,const char* where){if(!e->ExceptionCheck())return false;e->ExceptionDescribe();e->ExceptionClear();logf("JNI ERROR: %s; native controls disabled",where);disabled=true;return true;}
static jclass cls(JNIEnv* e,const char* n){jclass c=e->FindClass(n);if(!c)return nullptr;jclass r=(jclass)e->NewGlobalRef(c);e->DeleteLocalRef(c);return r;}
static bool foreground(){DWORD p=0;GetWindowThreadProcessId(GetForegroundWindow(),&p);return p==GetCurrentProcessId();}
static void key(WORD vk,bool down){INPUT in={};in.type=INPUT_KEYBOARD;in.ki.wVk=vk;in.ki.dwFlags=down?0:KEYEVENTF_KEYUP;SendInput(1,&in,sizeof(in));}
static void click(bool down){INPUT in={};in.type=INPUT_MOUSE;in.mi.dwFlags=down?MOUSEEVENTF_LEFTDOWN:MOUSEEVENTF_LEFTUP;SendInput(1,&in,sizeof(in));}
#include "mapper_async.h"
static float axis(SHORT v,int dz){int a=std::abs((int)v);if(a<=dz)return 0;return std::min(1.f,(a-dz)/float(32767-dz))*(v<0?-1.f:1.f);}
static bool initAPI(JNIEnv* e){
 if(apiReady)return true;
 sg=cls(e,"SoccerGame");go=cls(e,"GameObject");gs=cls(e,"GameSerializeSettings");sm=cls(e,"SoccerModule");mt=cls(e,"Match");tm=cls(e,"Team");tc=cls(e,"TeamController");analog=cls(e,"InputAnalog");digital=cls(e,"InputDigital");
 if(error(e,"class lookup"))return false;
 gameField=e->GetStaticFieldID(sg,"game","LSoccerGame;");settingsField=e->GetStaticFieldID(sg,"m_cSettings","LGameSerializeSettings;");resField=e->GetFieldID(gs,"m_Resolution","I");activeField=e->GetFieldID(sg,"activeMenu","I");moduleField=e->GetStaticFieldID(sg,"activeLevelModule","LSoccerModule;");
 matchField=e->GetStaticFieldID(sm,"m_cMatch","LAIMatch;");menuField=e->GetFieldID(sm,"m_bMenuVisible","Z");pauseField=e->GetFieldID(sm,"bPaused","Z");userField=e->GetFieldID(tm,"m_bUserControled","Z");ctrlField=e->GetFieldID(tm,"m_cTeamController","LTeamController;");focusField=e->GetFieldID(tm,"m_cFocusFBaller","LFootBaller;");keyField=e->GetFieldID(tc,"_KEY_STATES","I");tcTeamField=e->GetFieldID(tc,"m_cTeam","LAITeam;");
 setRes=e->GetMethodID(go,"SetResolution","(II)V");setFull=e->GetMethodID(go,"SetFullscreen","(Z)V");apply=e->GetMethodID(go,"ApplyVideoSettings","()V");screenW=e->GetStaticMethodID(go,"GetScreenWidth","()I");screenH=e->GetStaticMethodID(go,"GetScreenHeight","()I");loadFont=e->GetMethodID(go,"LoadFont","(Ljava/lang/String;Ljava/lang/String;I)Z");
 getTeam=e->GetMethodID(mt,"GetTeam","(I)LTeam;");analogCtor=e->GetMethodID(analog,"<init>","(IILTeamController;)V");digitalCtor=e->GetMethodID(digital,"<init>","(IIILTeamController;)V");analogMove=e->GetMethodID(analog,"Translate","(IIF)V");digitalButton=e->GetMethodID(digital,"Translate","(IIZ)V");
 if(error(e,"member lookup"))return false;apiReady=true;return true;
}
static void release(JNIEnv* e,Player& p){
 if(p.ctrl)e->SetIntField(p.ctrl,keyField,0);
 for(jobject b:p.buttons)if(b)e->DeleteGlobalRef(b);
 if(p.move)e->DeleteGlobalRef(p.move);if(p.special)e->DeleteGlobalRef(p.special);if(p.ctrl)e->DeleteGlobalRef(p.ctrl);p=Player();
}
static void bind(JNIEnv* e,Player& p,jobject c,int i){
 release(e,p);p.ctrl=e->NewGlobalRef(c);
 jobject a=e->NewObject(analog,analogCtor,i,3,c);p.move=e->NewGlobalRef(a);e->DeleteLocalRef(a);
 a=e->NewObject(analog,analogCtor,i,5,c);p.special=e->NewGlobalRef(a);e->DeleteLocalRef(a);
 const int actions[]={0,1,2,4};for(int b=0;b<4;b++){a=e->NewObject(digital,digitalCtor,i,actions[b],b,c);p.buttons[b]=e->NewGlobalRef(a);e->DeleteLocalRef(a);}
 logf("player %d bound to distinct TeamController, XInput port %d",i+1,ports[i]);
}
extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*,void*){return JNI_VERSION_1_2;}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_Initialize(JNIEnv*,jclass){
 if(initialized)return;initialized=true;char exe[MAX_PATH];GetModuleFileNameA(nullptr,exe,MAX_PATH);char* slash=strrchr(exe,'\\');if(slash)*slash=0;
 sprintf_s(ini,"%s\\CXSupport.ini",exe);sprintf_s(logpath,"%s\\CXSupport.log",exe);
 preset=std::clamp((int)GetPrivateProfileIntA("Video","Preset",3,ini),0,8);displayFullscreen=GetPrivateProfileIntA("Video","Fullscreen",preset>=6?1:0,ini)!=0;enabled=GetPrivateProfileIntA("Gamepad","Enabled",1,ini);
 for(int i=0;i<2;i++)ports[i]=std::clamp((int)GetPrivateProfileIntA("Gamepad",i?"Player2":"Player1",i,ini),0,3);
 if(ports[0]==ports[1])ports[1]=(ports[0]+1)%4;
 leftDZ=std::clamp((int)GetPrivateProfileIntA("Gamepad","LeftDeadzone",7849,ini),1000,30000);rightDZ=std::clamp((int)GetPrivateProfileIntA("Gamepad","RightDeadzone",8689,ini),1000,30000);cursorSpeed=std::clamp((int)GetPrivateProfileIntA("Gamepad","CursorSpeed",900,ini),100,4000);
 wchar_t sys[MAX_PATH];GetSystemDirectoryW(sys,MAX_PATH);wcscat_s(sys,L"\\xinput1_4.dll");xi=LoadLibraryW(sys);if(!xi){GetSystemDirectoryW(sys,MAX_PATH);wcscat_s(sys,L"\\xinput9_1_0.dll");xi=LoadLibraryW(sys);}if(xi)getState=(decltype(getState))GetProcAddress(xi,"XInputGetState");
 logf("HD native v1 initialized: preset=%d, XInput=%s, ports=%d/%d",preset,getState?"OK":"unavailable",ports[0],ports[1]);
 logf("DPI process aware=%d",IsProcessDPIAware());
 modernInit();
}
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_GetSelection(JNIEnv*,jclass){return preset;}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_ApplyVideoSettings(JNIEnv* e,jclass,jobject game){
 if(!initAPI(e))return;jobject settings=e->GetStaticObjectField(sg,settingsField);if(!settings)return;
 int requested=std::clamp((int)e->GetIntField(settings,resField),0,8);if(firstApply){requested=preset;firstApply=false;}
 displayNotice[0]=0;
 static const int widths[]={640,800,1024,1920,2560,3840,1920,2560,3840};static const int heights[]={480,600,768,1080,1440,2160,1080,1440,2160};
 bool full=displayFullscreen>=0?displayFullscreen!=0:requested>=6;
 if(full){bool found=false;DEVMODEW dm={};dm.dmSize=sizeof(dm);for(DWORD i=0;EnumDisplaySettingsW(nullptr,i,&dm);i++)if(dm.dmPelsWidth==(DWORD)widths[requested]&&dm.dmPelsHeight==(DWORD)heights[requested]&&dm.dmBitsPerPel==32){found=true;break;}
  if(!found){DEVMODEW desktop={};desktop.dmSize=sizeof(desktop);EnumDisplaySettingsW(nullptr,ENUM_CURRENT_SETTINGS,&desktop);int safe=2;for(int p=3;p<=4;p++)if(widths[p]+32<=(int)desktop.dmPelsWidth&&heights[p]+80<=(int)desktop.dmPelsHeight)safe=p;logf("fullscreen %dx%d unavailable; safe window %dx%d",widths[requested],heights[requested],widths[safe],heights[safe]);requested=safe;full=false;sprintf_s(displayNotice,"Tryb niedostepny.\nWybrano %dx%d okno.",widths[safe],heights[safe]);}}
 preset=requested;displayFullscreen=full?1:0;e->SetIntField(settings,resField,preset);
 e->CallVoidMethod(game,setFull,(jboolean)full);e->CallVoidMethod(game,setRes,widths[preset],heights[preset]);e->CallVoidMethod(game,apply);
 if(error(e,"video settings"))return;
 reviewGraphicsChanged();
 int w=e->CallStaticIntMethod(go,screenW),h=e->CallStaticIntMethod(go,screenH);logf("VIDEO requested=%dx%d %s, engine=%dx%d",widths[preset],heights[preset],full?"fullscreen":"window",w,h);
 char v[12];sprintf_s(v,"%d",preset);WritePrivateProfileStringA("Video","Preset",v,ini);WritePrivateProfileStringA("Video","Fullscreen",displayFullscreen?"1":"0",ini);e->DeleteLocalRef(settings);
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_LoadFont(JNIEnv* e,jclass,jobject obj,jstring id,jstring face,jint size){
 if(!initAPI(e))return JNI_FALSE;
 if(preset>=3){
  int originalSize=(int)size,h=e->CallStaticIntMethod(go,screenH);size=std::max(1,(int)std::lround(size*h/768.0));
  const char* originalFace=e->GetStringUTFChars(face,nullptr);const char* alias=nullptr;
  for(const auto& entry:cxBitmapFontAliases)if(entry.size==originalSize&&!strcmp(entry.face,originalFace)){alias=entry.alias;break;}
  e->ReleaseStringUTFChars(face,originalFace);
  if(alias){jstring bitmapFace=e->NewStringUTF(alias);jboolean result=e->CallBooleanMethod(obj,loadFont,id,bitmapFace,size);e->DeleteLocalRef(bitmapFace);return result;}
 }
 return e->CallBooleanMethod(obj,loadFont,id,face,size);
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_ShouldIgnoreKeys(JNIEnv* e,jclass,jobject c){
 if(!enabled||disabled||!foreground())return JNI_FALSE;for(Player& p:players)if(p.connected&&p.ctrl&&e->IsSameObject(p.ctrl,c))return JNI_TRUE;return JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_Tick(JNIEnv* e,jclass){
 if(disabled){reviewReleaseInjectedInput();return;}if(!initAPI(e)){reviewReleaseInjectedInput();return;}
 if(e->PushLocalFrame(64)<0){reviewReleaseInjectedInput();return;}
 DWORD now=GetTickCount();float dt=lastTick?std::min(.05f,(now-lastTick)*.001f):.016f;lastTick=now;
 if(!frameCount++)logf("frame hook active");
 bool fg=foreground();bool m=cxMapperPoll(now);if(m!=mapper)logf("AntiMicroX %s: native gameplay active; menu emulation %s",m?"detected":"absent",m?"delegated to mapper":"native");mapper=m;
 jobject game=e->GetStaticObjectField(sg,gameField);jobject module=e->GetStaticObjectField(sg,moduleField);jobject match=e->GetStaticObjectField(sm,matchField);
 bool inGame=game&&module&&match&&e->GetIntField(game,activeField)==2;
 bool menus=!inGame||(module&&(e->GetBooleanField(module,menuField)||e->GetBooleanField(module,pauseField)));
 modernFrame(e,game,module,inGame,menus);
 bool wantMouse=false,wantEscape=false,wantEnter=false;
 for(int i=0;i<2;i++){
  Player& p=players[i];
  jobject team=inGame?e->CallObjectMethod(match,getTeam,getPlayerTeam(e,match,i)):nullptr;
  jobject c=(team&&e->GetBooleanField(team,userField))?e->GetObjectField(team,ctrlField):nullptr;
  int chosenPort=c?padControllerPort(e,c):-1;
  bool nativeOwner=c&&chosenPort>=0;
  int inputPort=nativeOwner?chosenPort:ports[i];
  XINPUT_STATE s={};bool connected=enabled&&getState&&getState(inputPort,&s)==ERROR_SUCCESS;
  if(!nativeOwner)c=nullptr;
  bool ownedConnected=nativeOwner&&connected;
  if(c&&!e->IsSameObject(c,p.ctrl))bind(e,p,c,i);else if(!c&&p.ctrl)release(e,p);
  if(p.connected!=ownedConnected)logf("player %d pad %s",i+1,ownedConnected?"connected":"disconnected");p.connected=ownedConnected;
  WORD b=connected?s.Gamepad.wButtons:0;
  if(fg&&connected&&!mapper){
   wantEscape|=(b&XINPUT_GAMEPAD_BACK)!=0;wantEnter|=(b&XINPUT_GAMEPAD_START)!=0;
   float x=axis(s.Gamepad.sThumbRX,rightDZ),y=(padCursorInverted()?1.f:-1.f)*axis(s.Gamepad.sThumbRY,rightDZ);
   if(x||y){POINT pos;RECT client;HWND wnd=GetForegroundWindow();if(GetCursorPos(&pos)&&GetClientRect(wnd,&client)){POINT tl={0,0};ClientToScreen(wnd,&tl);pos.x=std::clamp(pos.x+(int)std::lround(x*cursorSpeed*dt),tl.x,tl.x+client.right-1);pos.y=std::clamp(pos.y+(int)std::lround(y*cursorSpeed*dt),tl.y,tl.y+client.bottom-1);SetCursorPos(pos.x,pos.y);}}
   if(menus&&(b&XINPUT_GAMEPAD_A))wantMouse=true;
  }
  if(!p.ctrl){p.previous=b;continue;}
  jobject focus=team?e->GetObjectField(team,focusField):nullptr;
  bool active=fg&&connected&&!menus&&focus;
  float x=active?axis(s.Gamepad.sThumbLX,leftDZ):0,y=active?-axis(s.Gamepad.sThumbLY,leftDZ):0;
  if(active){if(b&XINPUT_GAMEPAD_DPAD_LEFT)x=-1;if(b&XINPUT_GAMEPAD_DPAD_RIGHT)x=1;if(b&XINPUT_GAMEPAD_DPAD_UP)y=-1;if(b&XINPUT_GAMEPAD_DPAD_DOWN)y=1;}
  int mask=(x<-.1f?8:x>.1f?2:0)|(y<-.1f?1:y>.1f?4:0);
  if(focus&&(mask!=p.mask||mask)){
   e->SetIntField(p.ctrl,keyField,0);
   for(jobject a:{p.move,p.special}){e->CallVoidMethod(a,analogMove,i,0,x);e->CallVoidMethod(a,analogMove,i,1,y);}
  }else if(!active)e->SetIntField(p.ctrl,keyField,0);
  p.mask=mask;static const WORD buttons[]={XINPUT_GAMEPAD_A,XINPUT_GAMEPAD_B,XINPUT_GAMEPAD_X,XINPUT_GAMEPAD_Y};
  WORD actionButtons=active?b:0;
  for(int k=0;k<4;k++)if((p.previous&buttons[k])!=(actionButtons&buttons[k])){if(focus)e->CallVoidMethod(p.buttons[k],digitalButton,i,k,(jboolean)((actionButtons&buttons[k])!=0));}
  p.previous=actionButtons;
 }
 // The engine owns its integrated relative cursor; do not feed recentered OS coordinates back.
 reviewCommitInjectedInput(fg&&!mapper&&enabled&&!disabled,wantEscape,wantEnter,wantMouse);
 if(error(e,"frame input"))reviewReleaseInjectedInput();e->PopLocalFrame(nullptr);
}
#include "display_native.cpp"
#include "modern.cpp"
#include "commentator_visual.cpp"
#include "content.cpp"

#include "pad_controls.cpp"

#include "ext/physics/physics.cpp"

#include "review_runtime.cpp"
