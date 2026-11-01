// Cosmetic quote speaker only: the original sound scheduling/gameplay is kept.
static bool cxGothicSpeaking=false;
static DWORD cxQuoteStart=0,cxQuoteUntil=0;
static int cxQuoteIndex=-1,cxShownQuote=-1,cxQuoteWidth=0,cxQuoteHeight=0;
static jobject cxQuoteHud=nullptr,cxQuoteWidget=nullptr;
static bool cxQuoteVisible=false;
static unsigned cxQuoteEpoch=0;
static jclass cxQuoteVector=nullptr;
static jmethodID cxQuoteVectorCtor=nullptr,cxQuotePos=nullptr,cxQuoteSize=nullptr;
static void cxResetGothicQuote(JNIEnv* e){
 // Old native sprites may already be deleted. Release Java references only.
 if(cxQuoteHud)e->DeleteGlobalRef(cxQuoteHud);
 if(cxQuoteWidget)e->DeleteGlobalRef(cxQuoteWidget);
 cxQuoteHud=nullptr;cxQuoteWidget=nullptr;cxShownQuote=-1;cxQuoteIndex=-1;
 cxQuoteUntil=0;cxQuoteVisible=false;cxGothicSpeaking=false;cxQuoteEpoch=reviewGraphicsEpoch;
}

static void cxParrotVisible(JNIEnv* e,jobject commentator,bool visible){
 jclass c=e->GetObjectClass(commentator);
 jmethodID rendering=e->GetMethodID(c,"EnableRendering","(Z)V");
 if(rendering)e->CallVoidMethod(commentator,rendering,(jboolean)visible);
 e->DeleteLocalRef(c);
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_BeforeCommentary(JNIEnv* e,jclass,jobject commentator,jstring path){
 bool gothic=false;
 if(path){const char* value=e->GetStringUTFChars(path,nullptr);if(value){gothic=_strnicmp(value,"data/sounds/cx/quips/",21)==0;e->ReleaseStringUTFChars(path,value);}}
 cxGothicSpeaking=gothic;
 if(!gothic){cxQuoteUntil=0;cxParrotVisible(e,commentator,true);}
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_CommentaryVisual(JNIEnv* e,jclass,jobject commentator){
 cxParrotVisible(e,commentator,!cxGothicSpeaking);
}
static void cxStartGothicQuote(JNIEnv* e,jobject commentator,int event,int variant,float duration){
 static const int offsets[]={0,5,9,13};
 cxQuoteIndex=offsets[event]+variant;cxQuoteStart=GetTickCount();
 cxQuoteUntil=cxQuoteStart+(DWORD)(std::max(.5f,duration)*1000);
 cxParrotVisible(e,commentator,false);
}
static void cxUpdateGothicHud(JNIEnv* e,jobject hud,bool menu){
 if(cxQuoteEpoch!=reviewGraphicsEpoch)cxResetGothicQuote(e);
 if(!cxQuoteHud||!e->IsSameObject(cxQuoteHud,hud)){
  if(cxQuoteHud)e->DeleteGlobalRef(cxQuoteHud);
  if(cxQuoteWidget)e->DeleteGlobalRef(cxQuoteWidget);
  cxQuoteHud=e->NewGlobalRef(hud);cxQuoteWidget=nullptr;cxShownQuote=-1;cxQuoteVisible=false;
 }
 bool visible=voiceOn&&!menu&&cxGothicSpeaking&&cxQuoteIndex>=0&&(LONG)(cxQuoteUntil-GetTickCount())>0;
 if(visible&&cxShownQuote!=cxQuoteIndex){
  if(cxQuoteWidget){e->CallVoidMethod(cxQuoteWidget,setVisible,JNI_FALSE);e->DeleteGlobalRef(cxQuoteWidget);cxQuoteWidget=nullptr;}
  char id[40];sprintf_s(id,"CX_SPEAKER_%d",cxQuoteIndex);jobject widget=elem(e,hud,id);
  if(widget){cxQuoteWidget=e->NewGlobalRef(widget);e->DeleteLocalRef(widget);}
  cxShownQuote=cxQuoteIndex;cxQuoteVisible=false;
 }
 if(cxQuoteWidget&&visible!=cxQuoteVisible){
  e->CallVoidMethod(cxQuoteWidget,setVisible,(jboolean)visible);cxQuoteVisible=visible;
  if(visible){
   jobject tex=e->GetObjectField(cxQuoteWidget,e->GetFieldID(uw,"m_cNormalTexture","LUITexture;"));
   int id=0;if(tex){jclass tc=e->GetObjectClass(tex);id=e->GetIntField(tex,e->GetFieldID(tc,"m_nId","I"));e->DeleteLocalRef(tc);e->DeleteLocalRef(tex);}
   logf("GOTHIC SPEAKER index=%d texture=%d captions=off",cxQuoteIndex,id);
  }
 }
 if(!visible)return;
 cxQuoteWidth=e->CallStaticIntMethod(go,screenW);cxQuoteHeight=e->CallStaticIntMethod(go,screenH);
 if(!cxQuoteVector){cxQuoteVector=cls(e,"Vector");cxQuoteVectorCtor=e->GetMethodID(cxQuoteVector,"<init>","(FFF)V");cxQuotePos=e->GetMethodID(uw,"SetPos","(LVector;)V");cxQuoteSize=e->GetMethodID(uw,"SetSize","(LVector;)V");}
}
static void cxAnimateGothicQuote(JNIEnv* e,bool active){
 if(cxQuoteEpoch!=reviewGraphicsEpoch){cxResetGothicQuote(e);return;}
 if(!cxQuoteWidget||!cxQuoteVisible||!cxQuoteVector)return;
 DWORD now=GetTickCount();
 if(!active||!voiceOn||!cxGothicSpeaking||(LONG)(cxQuoteUntil-now)<=0){e->CallVoidMethod(cxQuoteWidget,setVisible,JNI_FALSE);cxQuoteVisible=false;return;}
 float enter=std::clamp((now-cxQuoteStart)/180.f,0.f,1.f);
 float leave=std::clamp((cxQuoteUntil-now)/160.f,0.f,1.f);
 float ease=std::min(enter*enter*(3-2*enter),leave*leave*(3-2*leave));
 float size=cxQuoteHeight*.28f;
 float x=.015f*cxQuoteWidth-(1-ease)*(size+.02f*cxQuoteWidth);
 float y=.63f*cxQuoteHeight+std::sin((now-cxQuoteStart)*.012f)*cxQuoteHeight*.002f;
 jobject pos=e->NewObject(cxQuoteVector,cxQuoteVectorCtor,x,y,0.f);
 jobject dims=e->NewObject(cxQuoteVector,cxQuoteVectorCtor,size,size,0.f);
 e->CallVoidMethod(cxQuoteWidget,cxQuotePos,pos);e->CallVoidMethod(cxQuoteWidget,cxQuoteSize,dims);
 e->DeleteLocalRef(pos);e->DeleteLocalRef(dims);
}
