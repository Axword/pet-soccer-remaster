// Optional integration helper. Include before SpawnBackdrop, then call once
// after that function has confirmed level 38..43 and the module is initialized.
// It only lowers genuinely floating small P38A..P43G neutral replacement props.
// It does not move the big backdrop, football objects, fences, terrain or actors.
static void cxGroundNeutralArenaDecor(JNIEnv* e,jobject module,int arena){
 if(!module||arena<38||arena>43||e->PushLocalFrame(32)<0)return;
 jclass objects=e->FindClass("GameObject"),control=e->FindClass("ControlObject"),mesh=e->FindClass("MeshObject"),vector=e->FindClass("Vector");
 jmethodID list=e->GetStaticMethodID(objects,"GetObjectsFromClassModule","(Ljava/lang/String;LModule;)[LGameObject;"),get=e->GetMethodID(control,"GetPositionVectorVolatile","()LVector;"),size=e->GetMethodID(objects,"GetTerrainSize","()LVector;"),terrain=e->GetMethodID(objects,"TerrainHeight","(FF)F"),extents=e->GetMethodID(mesh,"GetMeshExtentsInWorld","(LVector;LVector;)V"),set=e->GetMethodID(control,"SetPosition","(LVector;)V"),ctor=e->GetMethodID(vector,"<init>","(FFF)V");
 jfieldID filename=e->GetFieldID(mesh,"MeshName","Ljava/lang/String;"),vx=e->GetFieldID(vector,"fX","F"),vy=e->GetFieldID(vector,"fY","F"),vz=e->GetFieldID(vector,"fZ","F");
 if(e->ExceptionCheck()){e->ExceptionDescribe();e->ExceptionClear();logf("ARENA_DECOR_GROUND_API_ERROR map=%d",arena);e->PopLocalFrame(nullptr);return;}
 jobject dimensions=e->CallObjectMethod(module,size);float width=dimensions?e->GetFloatField(dimensions,vx):0,depth=dimensions?e->GetFloatField(dimensions,vz):0;
 if(!(std::isfinite(width)&&std::isfinite(depth)&&width>2&&depth>2)){e->PopLocalFrame(nullptr);return;}
 jstring type=e->NewStringUTF("MeshObject");jobjectArray all=(jobjectArray)e->CallStaticObjectMethod(objects,list,type,module);int matched=0,lowered=0;
 if(all)for(int i=0;i<e->GetArrayLength(all);i++){
  if(e->PushLocalFrame(12)<0)break;
  jobject object=e->GetObjectArrayElement(all,i);jstring name=object?(jstring)e->GetObjectField(object,filename):nullptr;
  if(!name){e->PopLocalFrame(nullptr);continue;}
  const char* raw=e->GetStringUTFChars(name,nullptr);char path[260];strncpy_s(path,raw,_TRUNCATE);e->ReleaseStringUTFChars(name,raw);
  for(char* p=path;*p;p++){if(*p=='\\')*p='/';else if(*p>='A'&&*p<='Z')*p=(char)(*p-'A'+'a');}
  char* base=strrchr(path,'/');base=base?base+1:path;char expected[8];sprintf_s(expected,"p%d",arena);
  bool neutral=strncmp(base,expected,3)==0&&base[3]>='a'&&base[3]<='g';const char* tail=base+4;
  if(neutral){while(*tail=='0')tail++;neutral=strcmp(tail,".3da")==0;}
  if(!neutral){e->PopLocalFrame(nullptr);continue;}matched++;
  jobject position=e->CallObjectMethod(object,get);if(!position){e->PopLocalFrame(nullptr);continue;}float x=e->GetFloatField(position,vx),y=e->GetFloatField(position,vy),z=e->GetFloatField(position,vz);
  if(!(std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z)&&x>=0&&x<width&&z>=0&&z<depth)){e->PopLocalFrame(nullptr);continue;}
  jobject lo=e->NewObject(vector,ctor,0.f,0.f,0.f),hi=e->NewObject(vector,ctor,0.f,0.f,0.f);e->CallVoidMethod(object,extents,lo,hi);
  float low=e->GetFloatField(lo,vy),high=e->GetFloatField(hi,vy),height=e->CallFloatMethod(module,terrain,std::clamp(x,.5f,width-1.f),std::clamp(z,.5f,depth-1.f));
  if(e->ExceptionCheck()){e->ExceptionDescribe();e->ExceptionClear();logf("ARENA_DECOR_GROUND_SAMPLE_ERROR map=%d mesh=%s",arena,path);e->PopLocalFrame(nullptr);continue;}
  float gap=low-height;
  if(std::isfinite(low)&&std::isfinite(high)&&low<=high&&std::isfinite(height)&&gap>2.f&&gap<5000.f){
   jobject placed=e->NewObject(vector,ctor,x,y-gap-1.f,z);e->CallVoidMethod(object,set,placed);lowered++;
   logf("ARENA_DECOR_GROUND map=%d mesh=%s bottom=%.3f terrain=%.3f deltaY=%.3f",arena,path,low,height,-gap-1.f);
  }
  e->PopLocalFrame(nullptr);
 }
 logf("ARENA_DECOR_GROUND_SUMMARY map=%d matched=%d lowered=%d",arena,matched,lowered);e->PopLocalFrame(nullptr);
}
