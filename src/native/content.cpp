#include "content_data.h"
#include "ext/hotfix-20261031/maps/ground_neutral_decor.cpp"
static jobject backdropOwner=nullptr;
static float originalPhysics[3]={};
extern "C" JNIEXPORT void JNICALL Java_CXSupport_NormalizePhysics(JNIEnv* e,jclass,jobject footballer){
 logf("NORMALIZE entering");
 jclass f=e->GetObjectClass(footballer);int animal=e->GetIntField(footballer,e->GetFieldID(f,"m_nAnimalType","I"));if(animal<13)return;
 e->PushLocalFrame(24);jclass v=e->FindClass("Vector");jmethodID ctor=e->GetMethodID(v,"<init>","(FFF)V");
 if(originalPhysics[1]<=0){
  logf("NORMALIZE loading reference");
  jclass m=e->FindClass("MeshObject"),c=e->FindClass("ControlObject");jobject module=e->CallObjectMethod(footballer,e->GetMethodID(go,"GetModule","()LModule;"));jstring type=e->NewStringUTF("MeshObject");jobject reference=e->CallObjectMethod(module,e->GetMethodID(go,"CreateObject","(Ljava/lang/String;)LGameObject;"),type);
  jstring path=e->NewStringUTF("data/meshes/animals/robocik.3da");e->CallVoidMethod(reference,e->GetMethodID(m,"LoadMesh","(Ljava/lang/String;)V"),path);e->CallVoidMethod(reference,e->GetMethodID(m,"EnableRendering","(Z)V"),JNI_FALSE);e->CallVoidMethod(reference,e->GetMethodID(c,"ReplaceCollFlags","(I)V"),0);e->CallVoidMethod(reference,e->GetMethodID(c,"SetFlags","(I)V"),0);
  jobject lo=e->NewObject(v,ctor,0.f,0.f,0.f),hi=e->NewObject(v,ctor,0.f,0.f,0.f);e->CallVoidMethod(reference,e->GetMethodID(m,"GetMeshExtents","(LVector;LVector;)V"),lo,hi);
  int i=0;for(const char* axis:{"fX","fY","fZ"}){jfieldID n=e->GetFieldID(v,axis,"F");originalPhysics[i++]=e->GetFloatField(hi,n)-e->GetFloatField(lo,n);}
  logf("ORIGINAL_ROBOT_PHYSICS dimensions=%.3f/%.3f/%.3f",originalPhysics[0],originalPhysics[1],originalPhysics[2]);
 }
 if(originalPhysics[0]>0&&originalPhysics[1]>0){jobject dims=e->NewObject(v,ctor,originalPhysics[0],originalPhysics[1],originalPhysics[2]);e->SetObjectField(footballer,e->GetFieldID(f,"vMeshExtents","LVector;"),dims);}
 error(e,"cosmetic model physics normalization");e->PopLocalFrame(nullptr);
}
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_ResolveAnimal(JNIEnv* e,jclass,jint team,jint animal){
 // CX_FAZBEAR_MIXED_SQUAD
 bool fazbear=animal==19||(animal>=80&&animal<86);
 if((!fazbear&&(animal<30||animal>=86||!appearanceGroup[animal]))||!initAPI(e))return animal;
 jobject match=e->GetStaticObjectField(sm,matchField);if(!match)return animal;jobject t=e->CallObjectMethod(match,getTeam,team);if(!t)return animal;
 jmethodID count=e->GetMethodID(tm,"GetFootBallerCount","()I");int slot=e->CallIntMethod(t,count)%7;int base=appearanceGroup[animal];int result=fazbear?fazbearSpecies[slot]:base+slot;
 logf("SQUAD team=%d slot=%d appearance=%d name=%s",team,slot,result,appearanceNames[result]?appearanceNames[result]:"missing");return result;
}
extern "C" JNIEXPORT jstring JNICALL Java_CXSupport_ResolvePlayerName(JNIEnv* e,jclass,jint animal,jstring old){if((animal==19||(animal>=30&&animal<86))&&appearanceNames[animal])return e->NewStringUTF(appearanceNames[animal]);return old;}
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_Home(JNIEnv*,jclass,jint animal){return animal>=0&&animal<86?contentHomes[animal]:-1;}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_SpawnBackdrop(JNIEnv* e,jclass,jobject module){
 logf("BACKDROP entering");
 if(!initAPI(e))return;jfieldID levelField=e->GetFieldID(sm,"m_nLevelID","I");int id=e->GetIntField(module,levelField);if(id<38||id>43)return;
 if(backdropOwner&&e->IsSameObject(backdropOwner,module))return;
 if(backdropOwner)e->DeleteGlobalRef(backdropOwner);backdropOwner=e->NewGlobalRef(module);
 cxGroundNeutralArenaDecor(e,module,id);
 e->PushLocalFrame(24);jclass mesh=e->FindClass("MeshObject"),ctrl=e->FindClass("ControlObject"),vec=e->FindClass("Vector"),flags=e->FindClass("EFlags");
 logf("BACKDROP map=%d create",id);
 jstring type=e->NewStringUTF("MeshObject");jobject object=e->CallObjectMethod(module,e->GetMethodID(go,"CreateObject","(Ljava/lang/String;)LGameObject;"),type);
 if(!object||error(e,"backdrop create")){e->PopLocalFrame(nullptr);return;}
 char path[100];sprintf_s(path,"data/meshes/objects/CXarena%d.3da",id);jstring name=e->NewStringUTF(path);e->CallVoidMethod(object,e->GetMethodID(mesh,"LoadMesh","(Ljava/lang/String;)V"),name);
 logf("BACKDROP loaded");
 e->CallVoidMethod(module,e->GetMethodID(e->FindClass("Module"),"AddControlObject","(LControlObject;)V"),object);e->CallVoidMethod(object,e->GetMethodID(mesh,"EnableRendering","(Z)V"),JNI_TRUE);if(error(e,"backdrop render registration")){e->PopLocalFrame(nullptr);return;}
 // MeshObject.OnCreate already disables physics; no second setup is needed.
 logf("BACKDROP static physics disabled by OnCreate");
 int mask=0;for(const char* n:{"_COLLISION","_BLOCK_TRACE","_BLOCK_MOVE","_FXPARTICLE_COLLISION","_PHYSICS_COL_CORRECTION"})mask|=e->GetStaticIntField(flags,e->GetStaticFieldID(flags,n,"I"));e->CallVoidMethod(object,e->GetMethodID(ctrl,"ClearFlag","(I)V"),mask);
 logf("BACKDROP trace flags cleared");
 jobject pos=e->NewObject(vec,e->GetMethodID(vec,"<init>","(FFF)V"),7502.989258f,6.25f,7520.986328f);e->CallVoidMethod(object,e->GetMethodID(ctrl,"SetPosition","(LVector;)V"),pos);logf("BACKDROP positioned");e->CallVoidMethod(object,e->GetMethodID(mesh,"SetLighting","(Z)V"),JNI_TRUE);logf("BACKDROP lighting set");
 // SetMeshVisibilityRange requires an engine LOD controller. This static
 // backdrop has none; its large bounds are handled by the ordinary culler.
 if(!error(e,"backdrop setup"))logf("BACKDROP map=%d collision/query disabled, file=%s",id,path);e->PopLocalFrame(nullptr);
}
