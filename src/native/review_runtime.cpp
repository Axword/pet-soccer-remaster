// Include last in the root translation unit. All calls run on the game thread.
// The integrator deliberately merges this helper; this review does not edit root.
static bool reviewEscapeDown=false,reviewEnterDown=false;

static HGLRC reviewContext=nullptr;
static void reviewCommitInjectedInput(bool allowed,bool escape,bool enter,bool mouse){
 escape=allowed&&escape;enter=allowed&&enter;mouse=allowed&&mouse;
 if(reviewEscapeDown!=escape){key(VK_ESCAPE,escape);reviewEscapeDown=escape;}
 if(reviewEnterDown!=enter){key(VK_RETURN,enter);reviewEnterDown=enter;}
 if(mouseDown!=mouse){click(mouse);mouseDown=mouse;}
}
static void reviewReleaseInjectedInput(){reviewCommitInjectedInput(false,false,false,false);}
static void reviewGraphicsChanged(){graphicsDirty=true;nextTexture=1;cxTextureScanAfter=GetTickCount()+400;maxAniso=1;reviewGraphicsEpoch++;}
static void reviewObserveContext(HGLRC context){if(context!=reviewContext){reviewContext=context;if(context)reviewGraphicsChanged();}}
struct ReviewBadge {jobject widget=nullptr,source=nullptr,texture=nullptr;unsigned epoch=0;};
static ReviewBadge reviewBadges[2];
static void reviewSetBadge(JNIEnv* e,jobject widget,jobject source,int player){
 ReviewBadge& b=reviewBadges[player];
 if(b.widget&&e->IsSameObject(widget,b.widget)&&b.source&&e->IsSameObject(source,b.source)&&b.epoch==reviewGraphicsEpoch)return;
 jclass textureClass=e->FindClass("UITexture");if(error(e,"badge texture class"))return;
 jmethodID ctor=e->GetMethodID(textureClass,"<init>","(LUIWindow;)V");
 jmethodID copy=e->GetMethodID(textureClass,"CopyTexture","(LUITexture;)V");
 jmethodID release=e->GetMethodID(uw,"ReleaseTexture","(LUITexture;)V");
 jfieldID normal=e->GetFieldID(uw,"m_cNormalTexture","LUITexture;"),id=e->GetFieldID(textureClass,"m_nId","I");
 if(error(e,"badge texture members"))return;
 // A current widget owns its cloned texture. A destroyed old widget's normal
 // texture is released by UIWindow.Remove/ReleaseTextures, so do not call it.
 if(b.widget&&e->IsSameObject(widget,b.widget)&&b.texture){
  jobject current=e->GetObjectField(widget,normal);
  if(current&&e->IsSameObject(current,b.texture))e->CallVoidMethod(widget,release,b.texture);
 }
 if(b.widget)e->DeleteGlobalRef(b.widget);if(b.source)e->DeleteGlobalRef(b.source);if(b.texture)e->DeleteGlobalRef(b.texture);b=ReviewBadge();
 jobject owned=e->NewObject(textureClass,ctor,widget);if(error(e,"badge texture allocation")||!owned)return;
 e->CallVoidMethod(owned,copy,source);if(error(e,"badge texture copy"))return;
 if(!e->GetIntField(owned,id)){e->CallVoidMethod(widget,setVisible,JNI_FALSE);return;}
 e->SetObjectField(widget,normal,owned);e->CallVoidMethod(widget,setTexture,owned);
 if(error(e,"badge texture assignment"))return;
 b.widget=e->NewGlobalRef(widget);b.source=e->NewGlobalRef(source);b.texture=e->NewGlobalRef(owned);b.epoch=reviewGraphicsEpoch;
}
static jobject reviewCamera=nullptr;
static int reviewAppliedFov=0;
static void reviewApplyCamera(JNIEnv* e,jobject module){
 if(!cameraFov&&!reviewAppliedFov)return;
 jobject camera=e->CallObjectMethod(module,e->GetMethodID(sm,"GetSoccerCamera","()LSoccerCamera;"));
 if(error(e,"camera lookup")||!camera)return;
 if(!reviewCamera||!e->IsSameObject(reviewCamera,camera)){if(reviewCamera)e->DeleteGlobalRef(reviewCamera);reviewCamera=e->NewGlobalRef(camera);reviewAppliedFov=0;}
 if(!cameraFov&&!reviewAppliedFov)return;
 jclass cameraClass=e->GetObjectClass(camera);
 jfieldID configured=e->GetFieldID(cameraClass,"m_fFOV","F");
 jmethodID set=e->GetMethodID(cameraClass,"SetFOV","(F)V");if(error(e,"camera FOV members"))return;
 // BaseCamera.<init> sets m_fFOV=60, and BaseCamera.OnCreate passes it directly
 // to SetFOV. Thus these values are degrees, and zero means restore that field.
 float original=e->GetFloatField(camera,configured);
 if(!std::isfinite(original)||original<=0||original>=179)original=60.f;
 float wanted=cameraFov?std::clamp((float)cameraFov,30.f,120.f):original;
 e->CallVoidMethod(camera,set,wanted);if(!error(e,"camera FOV"))reviewAppliedFov=cameraFov;
}
