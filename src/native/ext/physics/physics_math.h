#pragma once
#include <cmath>
#include <algorithm>
namespace cxphysics {
struct Vec { float x,y,z; };
struct Bounds { float x=0,z=0; bool valid=false; };
inline bool finite(Vec p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
inline bool outsideXZ(Vec p,Bounds b){return b.valid&&(p.x<0||p.z<0||p.x>=b.x||p.z>=b.z);}
inline bool escaped(Vec p,Bounds b,float ground){return !finite(p)||outsideXZ(p,b)||(std::isfinite(ground)&&p.y<ground-5000.f);}
inline float sample(float v,float size){return std::clamp(v,1.f,std::max(1.f,size-1.f));}
}
