// Include after globals/initAPI and before modern.cpp; no native UI ownership.
// displayFullscreen is declared next to preset, initialized from Video.Fullscreen.
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_DisplayResolutionIndex(JNIEnv*,jclass){return preset>=6?preset-3:preset;}
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_DisplayFullscreenSelection(JNIEnv*,jclass){return displayFullscreen>=0?displayFullscreen:(preset>=6?1:0);}
extern "C" JNIEXPORT jint JNICALL Java_CXSupport_ComposeDisplayPreset(JNIEnv*,jclass,jint resolution,jint mode){
 resolution=std::clamp((int)resolution,0,5);displayFullscreen=mode==1?1:0;
 return displayFullscreen&&resolution>=3?resolution+3:resolution;
}
