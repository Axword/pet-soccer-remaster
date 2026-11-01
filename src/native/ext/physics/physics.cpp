// Include after cxsupport.cpp / modern.cpp in the same translation unit.
// The game's original pitch-out and corner rules remain untouched for valid state.
#include "physics_math.h"
namespace cxp {
static bool ready=false,recovering=false;
static jclass ballClass,vectorClass,fieldClass,controlClass,gameClass,matchClass,aiClass,teamClass,soccerClass;
static jfieldID vx,vy,vz,centerField,ballField,matchField,prevField,curField,attachedField,hasOwnerField;
static jfieldID cornerField,scoreLeft,scoreRight,wasOut,wasCorner,wasGoal,specialField;
static jmethodID getPosition,getModule,getTerrainSize,terrainHeight,resetStart,detachBall,setPosition,vectorCtor;
static jmethodID getLogical,lineTop,lineBottom,lineEnd,matchState,ballSpecial,getTeam,getFootballer;
static jmethodID checkGoal,resetFlags,resetSpecial,setState;
static jobject boundsModule=nullptr;
static cxphysics::Bounds bounds;
static bool boundsLogged=false;
static unsigned recoveryCount=0,sampleClampCount=0;
static unsigned qaPass=0,qaFail=0;
static jclass classRef(JNIEnv* e,const char* name){jclass c=e->FindClass(name);if(!c)return nullptr;jclass r=(jclass)e->NewGlobalRef(c);e->DeleteLocalRef(c);return r;}
static bool failed(JNIEnv* e,const char* where){if(!e->ExceptionCheck())return false;logf("PHYSICS_API_ERROR %s",where);e->ExceptionDescribe();return true;}
static bool init(JNIEnv* e){
 if(ready)return true;
 ballClass=classRef(e,"Ball");vectorClass=classRef(e,"Vector");fieldClass=classRef(e,"GameField");controlClass=classRef(e,"ControlObject");gameClass=classRef(e,"GameObject");matchClass=classRef(e,"Match");aiClass=classRef(e,"AIMatch");teamClass=classRef(e,"Team");soccerClass=classRef(e,"SoccerModule");
 if(failed(e,"class lookup"))return false;
 vx=e->GetFieldID(vectorClass,"fX","F");vy=e->GetFieldID(vectorClass,"fY","F");vz=e->GetFieldID(vectorClass,"fZ","F");
 centerField=e->GetStaticFieldID(fieldClass,"cCenter","LFieldCenter;");ballField=e->GetStaticFieldID(fieldClass,"m_cBall","LBall;");cornerField=e->GetStaticFieldID(fieldClass,"cCornersTab","[LFieldCorner;");matchField=e->GetStaticFieldID(soccerClass,"m_cMatch","LAIMatch;");
 prevField=e->GetFieldID(ballClass,"m_cPrevOwner","LAIFootBaller;");curField=e->GetFieldID(ballClass,"m_cCurOwner","LAIFootBaller;");attachedField=e->GetFieldID(ballClass,"m_bAttached","Z");hasOwnerField=e->GetFieldID(ballClass,"m_bHasOwner","Z");specialField=e->GetFieldID(ballClass,"m_SpecialBallState","Z");
 wasOut=e->GetFieldID(ballClass,"m_bWasOut","Z");wasCorner=e->GetFieldID(ballClass,"m_bWasCorner","Z");wasGoal=e->GetFieldID(ballClass,"m_bWasGoal","Z");scoreLeft=e->GetFieldID(matchClass,"m_nScoreLeft","I");scoreRight=e->GetFieldID(matchClass,"m_nScoreRight","I");
 getPosition=e->GetMethodID(controlClass,"GetPositionVectorVolatile","()LVector;");getModule=e->GetMethodID(gameClass,"GetModule","()LModule;");getTerrainSize=e->GetMethodID(gameClass,"GetTerrainSize","()LVector;");terrainHeight=e->GetMethodID(gameClass,"TerrainHeight","(FF)F");
 resetStart=e->GetMethodID(ballClass,"ResetStartPosition","()V");detachBall=e->GetMethodID(ballClass,"BallDetachFromParentAndKeepWorldPos","()V");setPosition=e->GetMethodID(ballClass,"SetPosition","(LVector;)V");vectorCtor=e->GetMethodID(vectorClass,"<init>","(FFF)V");getLogical=e->GetMethodID(ballClass,"GetPositionLogVolatile","()LVector;");
 lineTop=e->GetStaticMethodID(fieldClass,"GetLineOutTopPos","()F");lineBottom=e->GetStaticMethodID(fieldClass,"GetLineOutBottomPos","()F");lineEnd=e->GetStaticMethodID(fieldClass,"GetEndLinePos","()F");matchState=e->GetStaticMethodID(aiClass,"GetMatchState","()I");setState=e->GetStaticMethodID(aiClass,"SetMatchState","(I)V");ballSpecial=e->GetMethodID(ballClass,"IsSpecialBall","()Z");
 getTeam=e->GetMethodID(matchClass,"GetTeam","(I)LTeam;");getFootballer=e->GetMethodID(teamClass,"GetFootBaller","(I)LFootBaller;");checkGoal=e->GetMethodID(ballClass,"CheckGoal","()V");resetFlags=e->GetMethodID(ballClass,"ResetEventFlags","()V");resetSpecial=e->GetMethodID(ballClass,"ResetSpecialBall","()V");
 if(failed(e,"member lookup"))return false;ready=true;return true;
}
static cxphysics::Vec read(JNIEnv* e,jobject v){return {e->GetFloatField(v,vx),e->GetFloatField(v,vy),e->GetFloatField(v,vz)};}
static jobject vector(JNIEnv* e,cxphysics::Vec p){return e->NewObject(vectorClass,vectorCtor,p.x,p.y,p.z);}
static bool center(JNIEnv* e,cxphysics::Vec& p){jobject c=e->GetStaticObjectField(fieldClass,centerField);if(!c)return false;jobject v=e->CallObjectMethod(c,getPosition);e->DeleteLocalRef(c);if(!v)return false;p=read(e,v);e->DeleteLocalRef(v);return cxphysics::finite(p);}
static cxphysics::Bounds getBounds(JNIEnv* e,jobject object){
 jobject module=e->CallObjectMethod(object,getModule);if(!module)return {};
 if(boundsModule&&!e->IsSameObject(boundsModule,module)){e->DeleteGlobalRef(boundsModule);boundsModule=nullptr;bounds={};boundsLogged=false;}
 if(!boundsModule)boundsModule=e->NewGlobalRef(module);e->DeleteLocalRef(module);
 if(bounds.valid)return bounds;
 jobject size=e->CallObjectMethod(object,getTerrainSize);if(!size)return {};cxphysics::Vec dim=read(e,size);e->DeleteLocalRef(size);
 cxphysics::Vec middle;bool hasCenter=center(e,middle);
 bounds={dim.x,dim.z,std::isfinite(dim.x)&&std::isfinite(dim.z)&&dim.x>2&&dim.z>2};
 if(bounds.valid&&hasCenter&&(middle.x<0||middle.x>=dim.x||middle.z<0||middle.z>=dim.z))bounds.valid=false;
 // Do not mistake half-extents or a different terrain origin for full dimensions.
 jobjectArray corners=(jobjectArray)e->GetStaticObjectField(fieldClass,cornerField);
 if(bounds.valid&&corners){for(jsize i=0;i<e->GetArrayLength(corners);i++){jobject corner=e->GetObjectArrayElement(corners,i);if(!corner)continue;jobject v=e->CallObjectMethod(corner,getPosition);if(v){auto p=read(e,v);if(cxphysics::outsideXZ(p,bounds))bounds.valid=false;e->DeleteLocalRef(v);}e->DeleteLocalRef(corner);}e->DeleteLocalRef(corners);}
 if(!boundsLogged){logf("PHYSICS_BOUNDS x=%.3f z=%.3f valid=%d center=%.3f/%.3f",dim.x,dim.z,bounds.valid,hasCenter?middle.x:-1.f,hasCenter?middle.z:-1.f);boundsLogged=true;}
 return bounds;
}
static bool recover(JNIEnv* e,jobject ball,const char* reason,cxphysics::Vec old){
 if(recovering)return false;cxphysics::Vec middle;if(!center(e,middle))return false;
 jobject match=e->GetStaticObjectField(soccerClass,matchField),activeBall=e->GetStaticObjectField(fieldClass,ballField);
 if(!match||!activeBall||!e->IsSameObject(ball,activeBall))return false;
 recovering=true;
 // ResetStartPosition alone does not clear these flags. Clear attachment first so
 // its SetPosition cannot take the local-owner branch with an already null owner.
 e->CallVoidMethod(ball,detachBall);e->SetBooleanField(ball,attachedField,JNI_FALSE);e->SetBooleanField(ball,hasOwnerField,JNI_FALSE);
 e->CallVoidMethod(ball,resetStart);e->SetBooleanField(ball,attachedField,JNI_FALSE);e->SetBooleanField(ball,hasOwnerField,JNI_FALSE);
 recovering=false;
 if(failed(e,"recover ball"))return false;
 recoveryCount++;logf("PHYSICS_RECOVERY reason=%s old=(%.3f,%.3f,%.3f) count=%u",reason,old.x,old.y,old.z,recoveryCount);return true;
}
}

extern "C" JNIEXPORT jfloat JNICALL Java_CXSupport_PhysicsTerrainHeight(JNIEnv* e,jclass,jobject object,jfloat x,jfloat z){
 if(!object||!cxp::init(e))return 0;auto b=cxp::getBounds(e,object);bool changed=false;
 if(!std::isfinite(x)||!std::isfinite(z)){cxphysics::Vec c;if(!cxp::center(e,c))return 0;x=c.x;z=c.z;changed=true;}
 if(b.valid){float nx=cxphysics::sample(x,b.x),nz=cxphysics::sample(z,b.z);changed|=nx!=x||nz!=z;x=nx;z=nz;}
 if(changed){cxp::sampleClampCount++;if(cxp::sampleClampCount<=8||cxp::sampleClampCount%100==0)logf("PHYSICS_TERRAIN_SAMPLE_CLAMP x=%.3f z=%.3f count=%u",x,z,cxp::sampleClampCount);}
 return e->CallFloatMethod(object,cxp::terrainHeight,x,z);
}
extern "C" JNIEXPORT jobject JNICALL Java_CXSupport_PhysicsSanitizePosition(JNIEnv* e,jclass,jobject ball,jobject desired){
 if(!ball||!desired||!cxp::init(e)||cxp::recovering)return desired;
 auto p=cxp::read(e,desired);bool attached=e->GetBooleanField(ball,cxp::attachedField)!=0;
 if(attached&&cxphysics::finite(p))return desired;
 cxphysics::Vec middle;if(!cxp::center(e,middle))return cxphysics::finite(p)?desired:cxp::vector(e,{0,1,0});
 if(cxphysics::escaped(p,cxp::getBounds(e,ball),middle.y)){
  if(cxp::recover(e,ball,!cxphysics::finite(p)?"nonfinite-set-position":"outside-world-set-position",p)){jobject out=e->CallObjectMethod(ball,cxp::getPosition);return out?out:cxp::vector(e,middle);}
  return cxp::vector(e,middle);
 }
 return desired;
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_PhysicsGuardBall(JNIEnv* e,jclass,jobject ball){
 if(!ball||!cxp::init(e)||cxp::recovering)return JNI_FALSE;cxphysics::Vec middle;if(!cxp::center(e,middle))return JNI_FALSE;
 jobject match=e->GetStaticObjectField(cxp::soccerClass,cxp::matchField);if(!match)return JNI_FALSE;
 jobject position=e->CallObjectMethod(ball,cxp::getPosition);if(!position)return JNI_FALSE;auto p=cxp::read(e,position);e->DeleteLocalRef(position);
 jobject cur=e->GetObjectField(ball,cxp::curField);bool attached=e->GetBooleanField(ball,cxp::attachedField)!=0;
 if(attached&&!cur){e->CallVoidMethod(ball,cxp::detachBall);e->SetBooleanField(ball,cxp::attachedField,JNI_FALSE);e->SetBooleanField(ball,cxp::hasOwnerField,JNI_FALSE);attached=false;logf("PHYSICS_RECOVERY detached orphan ball attachment");}
 if((!attached&&cxphysics::escaped(p,cxp::getBounds(e,ball),middle.y))||!cxphysics::finite(p))return cxp::recover(e,ball,"outside-world-physics",p)?JNI_TRUE:JNI_FALSE;
 if(e->CallStaticIntMethod(cxp::aiClass,cxp::matchState)!=0||e->CallBooleanMethod(ball,cxp::ballSpecial))return JNI_FALSE;
 jobject previous=e->GetObjectField(ball,cxp::prevField);if(previous){e->DeleteLocalRef(previous);return JNI_FALSE;}
 jobject logical=e->CallObjectMethod(ball,cxp::getLogical);if(!logical)return JNI_FALSE;auto q=cxp::read(e,logical);e->DeleteLocalRef(logical);
 float top=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineTop),bottom=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineBottom),end=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineEnd);
 bool outside=q.x>top||q.x<bottom||q.z<0||q.z>end;
 if(outside){if(cur){e->SetObjectField(ball,cxp::prevField,cur);logf("PHYSICS_RECOVERY last touch restored from current owner");return JNI_FALSE;}return cxp::recover(e,ball,"out-without-last-touch",p)?JNI_TRUE:JNI_FALSE;}
 return JNI_FALSE;
}

// Explicit test entry point. Never scheduled by the production patch.
// Run once per case in an isolated, fully initialized match on the game thread.
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_PhysicsQAStep(JNIEnv* e,jclass,jint n){
 if(!cxp::init(e))return JNI_FALSE;if(e->PushLocalFrame(64)<0)return JNI_FALSE;
 jobject ball=e->GetStaticObjectField(cxp::fieldClass,cxp::ballField),match=e->GetStaticObjectField(cxp::soccerClass,cxp::matchField);
 bool pass=false;
 if(!ball||!match){logf("PHYSICS_QA_NOT_READY case=%d",n);e->PopLocalFrame(nullptr);return JNI_FALSE;}
 cxphysics::Vec middle;if(!cxp::center(e,middle)){e->PopLocalFrame(nullptr);return JNI_FALSE;}
 auto b=cxp::getBounds(e,ball);int l=e->GetIntField(match,cxp::scoreLeft),r=e->GetIntField(match,cxp::scoreRight);
 float top=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineTop),bottom=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineBottom),end=e->CallStaticFloatMethod(cxp::fieldClass,cxp::lineEnd);
 if(n<0||n>17){logf("PHYSICS_QA_BAD_CASE %d",n);e->PopLocalFrame(nullptr);return JNI_FALSE;}
 // Reset only fixture state. Neither release code nor normal gameplay does this.
 e->CallVoidMethod(ball,cxp::detachBall);e->SetBooleanField(ball,cxp::attachedField,JNI_FALSE);e->SetBooleanField(ball,cxp::hasOwnerField,JNI_FALSE);e->SetObjectField(ball,cxp::curField,nullptr);
 e->CallVoidMethod(ball,cxp::resetSpecial);e->CallVoidMethod(ball,cxp::resetStart);e->CallStaticVoidMethod(cxp::aiClass,cxp::setState,0);
 jobject team=e->CallObjectMethod(match,cxp::getTeam,n<8?(n%2):0);jobject owner=team?e->CallObjectMethod(team,cxp::getFootballer,1):nullptr;
 e->SetObjectField(ball,cxp::prevField,n<8?owner:nullptr);
 if(n<8){
  // Four touchline locations and four goal-line locations (outside the goalmouth).
  float x=(top+bottom)*.5f,z=end*.5f;
  if(n<4){x=n<2?top+100:bottom-100;z=end*((n%2)? .75f:.25f);}
  else {x=(top+bottom)*.5f+(n%2?1.f:-1.f)*(top-bottom)*.3f;z=n<6?-100:end+100;}
  jobject logical=cxp::vector(e,{x,0,z});jmethodID toWorld=e->GetStaticMethodID(cxp::fieldClass,"FieldToWorld","(LVector;)LVector;");jobject world=e->CallStaticObjectMethod(cxp::fieldClass,toWorld,logical);
  e->CallVoidMethod(ball,cxp::setPosition,world);e->CallVoidMethod(ball,cxp::checkGoal);
  int state=e->CallStaticIntMethod(cxp::aiClass,cxp::matchState);
  pass=owner&&(n<4?state==5:(state==4||state==6));
  logf("PHYSICS_QA_STANDARD case=%d actual_state=%d expected=%s",n,state,n<4?"OUT(5)":"CORNER(4)/GK(6)");
 }else if(n<12){
  // Escape beyond each complete terrain boundary; SetPosition must recover first.
  cxphysics::Vec p=middle;p.y+=50;
  if(n==8)p.x=-100;if(n==9)p.x=b.x+100;if(n==10)p.z=-100;if(n==11)p.z=b.z+100;
  unsigned before=cxp::recoveryCount;jobject v=cxp::vector(e,p);e->CallVoidMethod(ball,cxp::setPosition,v);e->CallVoidMethod(ball,cxp::checkGoal);jobject now=e->CallObjectMethod(ball,cxp::getPosition);auto q=cxp::read(e,now);
  pass=b.valid&&cxp::recoveryCount>before&&cxphysics::finite(q)&&!cxphysics::outsideXZ(q,b)&&std::abs(q.x-middle.x)<2&&std::abs(q.z-middle.z)<2;
 }else if(n==12||n==13){
  // Unknown last touch on a touchline / goal-line: must not dereference null.
  jobject logical=cxp::vector(e,{n==12?top+100:(top+bottom)*.5f+(top-bottom)*.3f,0,n==12?end*.5f:-100});jobject world=e->CallStaticObjectMethod(cxp::fieldClass,e->GetStaticMethodID(cxp::fieldClass,"FieldToWorld","(LVector;)LVector;"),logical);
  unsigned before=cxp::recoveryCount;e->CallVoidMethod(ball,cxp::setPosition,world);e->CallVoidMethod(ball,cxp::checkGoal);
  pass=cxp::recoveryCount>before&&!e->GetBooleanField(ball,cxp::wasOut)&&!e->GetBooleanField(ball,cxp::wasCorner)&&e->CallStaticIntMethod(cxp::aiClass,cxp::matchState)==0;
 }else if(n==14||n==15){
  // Non-finite incoming positions must be replaced BEFORE the engine sees them.
  cxphysics::Vec p=middle;if(n==14)p.x=NAN;else p.z=INFINITY;
  unsigned before=cxp::recoveryCount;jobject v=cxp::vector(e,p);e->CallVoidMethod(ball,cxp::setPosition,v);jobject now=e->CallObjectMethod(ball,cxp::getPosition);auto q=cxp::read(e,now);
  pass=cxp::recoveryCount>before&&cxphysics::finite(q)&&!cxphysics::outsideXZ(q,b);
 }else if(n==16){
  // Direct terrain samples outside map and with NaN cannot reach the native sampler.
  float a=Java_CXSupport_PhysicsTerrainHeight(e,nullptr,ball,-100,b.z+100),c=Java_CXSupport_PhysicsTerrainHeight(e,nullptr,ball,NAN,INFINITY);pass=b.valid&&std::isfinite(a)&&std::isfinite(c);
 }else{
  // A real current owner is preserved as last toucher, rather than inventing a player.
  e->SetObjectField(ball,cxp::curField,owner);e->SetBooleanField(ball,cxp::hasOwnerField,JNI_TRUE);e->SetObjectField(ball,cxp::prevField,nullptr);
  jobject logical=cxp::vector(e,{top+100,0,end*.5f});jobject world=e->CallStaticObjectMethod(cxp::fieldClass,e->GetStaticMethodID(cxp::fieldClass,"FieldToWorld","(LVector;)LVector;"),logical);e->CallVoidMethod(ball,cxp::setPosition,world);e->CallVoidMethod(ball,cxp::checkGoal);
  jobject prev=e->GetObjectField(ball,cxp::prevField);pass=owner&&prev&&e->IsSameObject(prev,owner)&&e->CallStaticIntMethod(cxp::aiClass,cxp::matchState)==5;
 }
 pass=pass&&l==e->GetIntField(match,cxp::scoreLeft)&&r==e->GetIntField(match,cxp::scoreRight)&&!e->ExceptionCheck();
 if(pass)cxp::qaPass++;else cxp::qaFail++;
 logf("PHYSICS_QA_%s case=%d score=%d:%d total_pass=%u total_fail=%u",pass?"PASS":"FAIL",n,e->GetIntField(match,cxp::scoreLeft),e->GetIntField(match,cxp::scoreRight),cxp::qaPass,cxp::qaFail);
 e->PopLocalFrame(nullptr);return pass?JNI_TRUE:JNI_FALSE;
}
