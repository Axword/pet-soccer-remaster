#include "physics_math.h"
#include <cstdio>
#include <limits>
int main(){
 using namespace cxphysics;Bounds world{15000,15000,true};unsigned checked=0,failed=0;
 auto check=[&](bool ok,const char* what){checked++;if(!ok){failed++;std::printf("FAIL %s\n",what);}};
 check(!escaped({7500,6,7500},world,6),"center remains valid");
 // Every real touchline / goal-line out near the original 3.2km x 5.8km pitch
 // remains a valid WORLD point and must be left to original match rules.
 for(float x:{5700.f,5900.f,9100.f,9300.f})for(float z:{4400.f,4600.f,10400.f,10600.f})check(!escaped({x,60,z},world,6),"ordinary out remains original");
 check(escaped({-1,6,7500},world,6),"negative X world escape");check(escaped({15000,6,7500},world,6),"upper X world escape");check(escaped({7500,6,-1},world,6),"negative Z world escape");check(escaped({7500,6,15000},world,6),"upper Z world escape");
 check(escaped({7500,-5001,7500},world,6),"lost underground ball");check(!escaped({7500,2500,7500},world,6),"high lob remains unchanged");
 check(escaped({NAN,6,7500},world,6),"NaN rejected");check(escaped({7500,INFINITY,7500},world,6),"infinity rejected");
 for(int i=-100;i<=15100;i++){float s=sample((float)i,world.x);check(std::isfinite(s)&&s>=1&&s<=14999,"terrain sample always inside edge");if(i>=1&&i<=14999)check(s==i,"interior samples unchanged");}
 check(!outsideXZ({-100,6,7500},{0,0,false}),"unknown bounds are not guessed");
 std::printf("physics math: %u checks, %u failures\n",checked,failed);return failed?1:0;
}
