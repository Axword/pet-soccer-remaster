// Four bounded widget slots; reuse layout/text unless their actual value changed.
struct CXHudCache {jobject widget=nullptr;std::wstring value;int height=-1;unsigned epoch=0;int visible=-1;};
static CXHudCache cxHudCaches[4];
static CXHudCache& cxHudCache(JNIEnv* e,jobject widget,int index){
 CXHudCache& c=cxHudCaches[index];
 if(!c.widget||!e->IsSameObject(c.widget,widget)){
  if(c.widget)e->DeleteGlobalRef(c.widget);c=CXHudCache();c.widget=e->NewGlobalRef(widget);
 }
 return c;
}
static void cxHudFont(JNIEnv* e,jobject widget,int index,jstring font,int height,jmethodID method){
 CXHudCache& c=cxHudCache(e,widget,index);
 if(c.height!=height||c.epoch!=reviewGraphicsEpoch){e->CallBooleanMethod(widget,method,font);c.height=height;c.epoch=reviewGraphicsEpoch;}
}
static void cxHudVisible(JNIEnv* e,jobject widget,int index,bool visible){
 CXHudCache& c=cxHudCache(e,widget,index);
 if(c.visible!=(int)visible){e->CallVoidMethod(widget,setVisible,(jboolean)visible);c.visible=visible;}
}
static void cxHudText(JNIEnv* e,jobject widget,int index,const wchar_t* textValue){
 CXHudCache& c=cxHudCache(e,widget,index);
 if(c.value==textValue)return;
 jstring value=e->NewString((const jchar*)textValue,(jsize)wcslen(textValue));
 e->CallVoidMethod(widget,setText,value);e->DeleteLocalRef(value);c.value=textValue;
}
