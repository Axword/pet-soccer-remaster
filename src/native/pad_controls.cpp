// Include after bridge helpers and modern.cpp. Tick needs forward declarations:
// static int padControllerPort(JNIEnv*,jobject);
// static void padSaveModernPorts(JNIEnv*);
// Uses existing root symbols: sg/go/tc/gameField/ports/enabled/getState/ini/logf/error.
static bool padReady=false;
static jclass padMenu,padCombo,padList,padEdit,padKb,padWindow,padStatic,padUIEdit;
static jfieldID padCombos[2],padKeys[2],padListField,padWorkField,padJoyField,padKeyField,padEditTextField,padParentField,padIdField,padPortField,padDeviceField,padJoyNumberField,padSavedKeysField;
static jmethodID padAddItem,padGetCount,padGetSel,padSetSel,padRefresh,padClearList,padGetItem,padSetText,padUpdateText,padGetKey,padSetKey,padGetKbs[2],padResetKeys,padSetLegacy,padGetElem,padSetVisible,padIsVisible;
static int padKeyboard[2][8]={{200,208,203,205,25,24,38,37},{17,31,30,32,20,34,35,22}};
static int padPrevSelection[2]={0,0};
static DWORD padLastRefresh=0;
static int padLastConnectedMask=-1;

static bool padAPI(JNIEnv* e){
 if(padReady)return true;
 if(!apiReady&&!initAPI(e))return false;
 padMenu=cls(e,"MenuOptionsControls");padCombo=cls(e,"UIComboBox");padList=cls(e,"UIListBox");padEdit=cls(e,"UIEditSelKey");padKb=cls(e,"KbSettings");padWindow=cls(e,"UIWindow");padStatic=cls(e,"UIStatic");padUIEdit=cls(e,"UIEdit");
 if(error(e,"pad menu classes"))return false;
 for(int i=0;i<2;i++){
  padCombos[i]=e->GetFieldID(padMenu,i?"m_cController2":"m_cController1","LUIComboBox;");
  padKeys[i]=e->GetFieldID(padMenu,i?"m_tKeys2":"m_tKeys1","[LUIEditSelKey;");
  padGetKbs[i]=e->GetStaticMethodID(sg,i?"GetKb1":"GetKb0","()LKbSettings;");
 }
 padListField=e->GetFieldID(padCombo,"m_cList","LUIListBox;");padWorkField=e->GetFieldID(padEdit,"m_bCanWork","Z");padJoyField=e->GetFieldID(padEdit,"m_nJoy","I");padKeyField=e->GetFieldID(padEdit,"m_nKey","I");padEditTextField=e->GetFieldID(padUIEdit,"m_sEditText","Ljava/lang/String;");
 padParentField=e->GetFieldID(padWindow,"m_wndParent","LUIWindow;");padIdField=e->GetFieldID(padWindow,"m_sId","Ljava/lang/String;");padPortField=e->GetFieldID(tc,"CXInputPort","I");padDeviceField=e->GetFieldID(padKb,"m_Device","I");padJoyNumberField=e->GetFieldID(padKb,"m_JoyNumber","I");padSavedKeysField=e->GetFieldID(padKb,"m_Keys","[I");
 padAddItem=e->GetMethodID(padCombo,"AddItem","(Ljava/lang/String;Ljava/lang/Object;)I");padGetCount=e->GetMethodID(padCombo,"GetItemCount","()I");padGetSel=e->GetMethodID(padCombo,"GetSelection","()I");padSetSel=e->GetMethodID(padCombo,"SetSelection","(I)V");padRefresh=e->GetMethodID(padCombo,"ForceRefresh","()V");padClearList=e->GetMethodID(padList,"Clear","()V");padGetItem=e->GetMethodID(padList,"GetItem","(I)LUIButton;");padSetText=e->GetMethodID(padStatic,"SetText","(Ljava/lang/String;)V");padUpdateText=e->GetMethodID(padUIEdit,"UpdateText","()V");padGetKey=e->GetMethodID(padEdit,"GetKey","()I");padSetKey=e->GetMethodID(padEdit,"SetKey","(I)V");
 padResetKeys=e->GetMethodID(padMenu,"ResetKeys","(I)V");padSetLegacy=e->GetMethodID(padMenu,"SetJoyStick","(LUIComboBox;[LUIEditSelKey;I)V");padGetElem=e->GetMethodID(padWindow,"GetElem","(Ljava/lang/String;)LUIWindow;");padSetVisible=e->GetMethodID(padWindow,"SetVisible","(Z)V");padIsVisible=e->GetMethodID(padWindow,"IsActuallyVisible","()Z");
 if(error(e,"pad menu members"))return false;padReady=true;return true;
}
static bool padConnected(int port){XINPUT_STATE s={};return getState&&port>=0&&port<4&&getState(port,&s)==ERROR_SUCCESS;}
static void padDeviceLabel(char* out,size_t count,int port){sprintf_s(out,count,"Pad %d XInput [%s]",port+1,padConnected(port)?"OK":"brak");}
static jobject padGetCombo(JNIEnv* e,jobject menu,int player){return e->GetObjectField(menu,padCombos[player]);}
static int padSelection(JNIEnv* e,jobject menu,int player){jobject c=padGetCombo(e,menu,player);if(!c)return 0;int n=e->CallIntMethod(c,padGetSel);e->DeleteLocalRef(c);return n;}
static jobject padKbFor(JNIEnv* e,int player){return e->CallStaticObjectMethod(sg,padGetKbs[player]);}
static void padSetControlVisible(JNIEnv* e,jobject root,const char* id,bool visible){jstring s=e->NewStringUTF(id);jobject o=e->CallObjectMethod(root,padGetElem,s);if(o){if(visible){jstring font=e->NewStringUTF("CXPadHint");e->CallBooleanMethod(o,e->GetMethodID(padWindow,"SetFont","(Ljava/lang/String;)Z"),font);e->DeleteLocalRef(font);jstring hint=e->NewStringUTF("RS: kursor / A: klik / Back: Esc / Start: Enter");e->CallVoidMethod(o,padSetText,hint);e->DeleteLocalRef(hint);}e->CallVoidMethod(o,padSetVisible,(jboolean)visible);}e->DeleteLocalRef(s);if(o)e->DeleteLocalRef(o);}
static void padRememberKeyboard(JNIEnv* e,jobject menu,int player){
 jobjectArray keys=(jobjectArray)e->GetObjectField(menu,padKeys[player]);if(!keys)return;
 for(int k=0;k<8;k++){jobject edit=e->GetObjectArrayElement(keys,k);if(edit){int code=e->CallIntMethod(edit,padGetKey);if(code>=0&&code<1000)padKeyboard[player][k]=code;e->DeleteLocalRef(edit);}}
 e->DeleteLocalRef(keys);
}
static void padDisplaySelection(JNIEnv* e,jobject menu,int player,int selection,bool capturePrevious){
 if(capturePrevious&&padPrevSelection[player]==0)padRememberKeyboard(e,menu,player);
 jobject combo=padGetCombo(e,menu,player);jobjectArray keys=(jobjectArray)e->GetObjectField(menu,padKeys[player]);if(!combo||!keys)return;
 bool xinput=selection>=1&&selection<=4;
 static const char* layout[]={"LS gora","LS dol","LS lewo","LS prawo","A","B","X","Y"};
 if(xinput){
  for(int k=0;k<8;k++){jobject edit=e->GetObjectArrayElement(keys,k);if(!edit)continue;e->SetBooleanField(edit,padWorkField,JNI_FALSE);e->SetIntField(edit,padJoyField,-1);jstring s=e->NewStringUTF(layout[k]);e->SetObjectField(edit,padEditTextField,s);e->CallVoidMethod(edit,padUpdateText);e->DeleteLocalRef(s);e->DeleteLocalRef(edit);}
 }else if(selection==0){
  for(int k=0;k<8;k++){jobject edit=e->GetObjectArrayElement(keys,k);if(!edit)continue;e->SetBooleanField(edit,padWorkField,JNI_TRUE);e->SetIntField(edit,padJoyField,-1);e->CallVoidMethod(edit,padSetKey,padKeyboard[player][k]);e->DeleteLocalRef(edit);}
 }else{
  e->CallVoidMethod(menu,padResetKeys,player);
  for(int k=0;k<8;k++){jobject edit=e->GetObjectArrayElement(keys,k);if(edit){e->SetBooleanField(edit,padWorkField,JNI_TRUE);e->DeleteLocalRef(edit);}}
  e->CallVoidMethod(menu,padSetLegacy,combo,keys,selection-5);
 }
 padPrevSelection[player]=selection;
 padSetControlVisible(e,menu,player?"CX_PAD_HINT2":"CX_PAD_HINT1",xinput);
 e->CallVoidMethod(combo,padRefresh);e->DeleteLocalRef(combo);e->DeleteLocalRef(keys);
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_PadFillCombo(JNIEnv* e,jclass,jobject combo){
 if(!padAPI(e)||!combo)return;
 jobject list=e->GetObjectField(combo,padListField);if(list&&e->CallIntMethod(combo,padGetCount)>0)e->CallVoidMethod(list,padClearList);
 jstring s=e->NewStringUTF("Klawiatura");e->CallIntMethod(combo,padAddItem,s,nullptr);e->DeleteLocalRef(s);
 for(int port=0;port<4;port++){char label[60];padDeviceLabel(label,sizeof(label),port);s=e->NewStringUTF(label);e->CallIntMethod(combo,padAddItem,s,nullptr);e->DeleteLocalRef(s);}
 jobject game=e->GetStaticObjectField(sg,gameField);int count=game?e->CallIntMethod(game,e->GetMethodID(go,"GetJoysticksCount","()I")):0;count=std::clamp(count,0,2);
 for(int n=0;n<count;n++){char label[60];sprintf_s(label,"Joystick %d (stary)",n+1);s=e->NewStringUTF(label);e->CallIntMethod(combo,padAddItem,s,nullptr);e->DeleteLocalRef(s);}
 e->CallVoidMethod(combo,padSetSel,0);if(list)e->DeleteLocalRef(list);if(game)e->DeleteLocalRef(game);error(e,"fill controller combo");
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_PadShowControls(JNIEnv* e,jclass,jobject menu){
 if(!padAPI(e))return;
 jstring hintId=e->NewStringUTF("CXPadHint"),hintFace=e->NewStringUTF("FL Romanski 13");e->CallBooleanMethod(menu,loadFont,hintId,hintFace,(jint)std::max(10,(int)e->CallStaticIntMethod(go,screenH)/48));e->DeleteLocalRef(hintId);e->DeleteLocalRef(hintFace);
 for(int i=0;i<2;i++){
  jobject combo=padGetCombo(e,menu,i);Java_CXSupport_PadFillCombo(e,nullptr,combo);jobject kb=padKbFor(e,i);if(!kb)continue;
  int device=e->GetIntField(kb,padDeviceField),port=e->GetIntField(kb,padJoyNumberField);int selected=device==3?std::clamp(port,0,3)+1:device==0?0:std::clamp(port,0,1)+5;
  if(selected>=e->CallIntMethod(combo,padGetCount))selected=0;
  jintArray saved=(jintArray)e->GetObjectField(kb,padSavedKeysField);jint codes[8];e->GetIntArrayRegion(saved,0,8,codes);
  for(int k=0;k<8;k++)if(codes[k]>=0&&codes[k]<1000)padKeyboard[i][k]=codes[k];
  e->CallVoidMethod(menu,padResetKeys,i);e->CallVoidMethod(combo,padSetSel,selected);padDisplaySelection(e,menu,i,selected,false);
  e->DeleteLocalRef(saved);e->DeleteLocalRef(kb);e->DeleteLocalRef(combo);
 }
 padLastRefresh=0;padLastConnectedMask=-1;error(e,"show controller settings");
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_PadSelectControls(JNIEnv* e,jclass,jobject menu,jobject button){
 if(!padAPI(e)||!button)return;jobject combo=e->NewLocalRef(button);
 for(int depth=0;depth<8&&!e->IsInstanceOf(combo,padCombo);depth++){jobject p=e->GetObjectField(combo,padParentField);e->DeleteLocalRef(combo);combo=p;if(!combo)return;}
 if(!e->IsInstanceOf(combo,padCombo)){e->DeleteLocalRef(combo);return;}
 for(int i=0;i<2;i++){jobject own=padGetCombo(e,menu,i);bool same=e->IsSameObject(own,combo);e->DeleteLocalRef(own);if(!same)continue;int selected=e->CallIntMethod(combo,padGetSel);
  // A single physical device cannot own both teams.
  if(selected>0&&padSelection(e,menu,1-i)==selected){jobject other=padGetCombo(e,menu,1-i);e->CallVoidMethod(other,padSetSel,0);padDisplaySelection(e,menu,1-i,0,true);e->DeleteLocalRef(other);}
  padDisplaySelection(e,menu,i,selected,true);break;
 }
 e->DeleteLocalRef(combo);error(e,"select controller");
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_PadSaveControls(JNIEnv* e,jclass,jobject menu){
 if(!padAPI(e))return;for(int i=0;i<2;i++){
  int selected=padSelection(e,menu,i);if(i==1&&selected>0&&selected==padSelection(e,menu,0))selected=0;
  jobject kb=padKbFor(e,i);if(!kb)continue;
  if(selected>=1&&selected<=4){e->SetIntField(kb,padDeviceField,3);e->SetIntField(kb,padJoyNumberField,selected-1);ports[i]=selected-1;}
  else{
   e->SetIntField(kb,padDeviceField,selected==0?0:1);e->SetIntField(kb,padJoyNumberField,selected==0?0:selected-5);
   jobjectArray edits=(jobjectArray)e->GetObjectField(menu,padKeys[i]);jintArray saved=(jintArray)e->GetObjectField(kb,padSavedKeysField);
   for(int k=0;k<8;k++){jobject edit=e->GetObjectArrayElement(edits,k);if(edit){jint key=e->CallIntMethod(edit,padGetKey);e->SetIntArrayRegion(saved,k,1,&key);e->DeleteLocalRef(edit);}}
   e->DeleteLocalRef(edits);e->DeleteLocalRef(saved);
  }
  e->DeleteLocalRef(kb);
 }
 WritePrivateProfileStringA("Gamepad","ProfileModeInitialized","1",ini);
 char v[12];for(int i=0;i<2;i++){sprintf_s(v,"%d",ports[i]);WritePrivateProfileStringA("Gamepad",i?"Player2":"Player1",v,ini);}
 error(e,"save controller settings");
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_PadAllAssigned(JNIEnv* e,jclass,jobject menu){
 if(!padAPI(e))return JNI_FALSE;for(int i=0;i<2;i++){int selected=padSelection(e,menu,i);if(selected>=1&&selected<=4)continue;jobjectArray keys=(jobjectArray)e->GetObjectField(menu,padKeys[i]);for(int k=selected==0?0:4;k<8;k++){jobject edit=e->GetObjectArrayElement(keys,k);if(edit){int code=e->CallIntMethod(edit,padGetKey);e->DeleteLocalRef(edit);if(code<0){e->DeleteLocalRef(keys);return JNI_FALSE;}}}e->DeleteLocalRef(keys);}return JNI_TRUE;
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_PadControlsFrame(JNIEnv* e,jclass,jobject menu){
 DWORD now=GetTickCount();if(now-padLastRefresh<500||!padAPI(e)||!e->CallBooleanMethod(menu,padIsVisible))return;padLastRefresh=now;
 int mask=0;for(int n=0;n<4;n++)if(padConnected(n))mask|=1<<n;if(mask==padLastConnectedMask)return;padLastConnectedMask=mask;
 for(int i=0;i<2;i++){jobject combo=padGetCombo(e,menu,i);jobject list=e->GetObjectField(combo,padListField);if(!list)continue;int selected=e->CallIntMethod(combo,padGetSel);for(int n=0;n<4;n++){jobject item=e->CallObjectMethod(list,padGetItem,n+1);if(item){char label[60];padDeviceLabel(label,sizeof(label),n);jstring s=e->NewStringUTF(label);e->CallVoidMethod(item,padSetText,s);e->DeleteLocalRef(s);e->DeleteLocalRef(item);}}e->CallVoidMethod(combo,padSetSel,selected);e->CallVoidMethod(combo,padRefresh);e->DeleteLocalRef(list);e->DeleteLocalRef(combo);}error(e,"controller hotplug status");
}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_PadUICommand(JNIEnv* e,jclass,jobject menu,jobject control,jint command){
 if((command!=0&&command!=2)||!control||!padAPI(e))return JNI_FALSE;jstring id=(jstring)e->GetObjectField(control,padIdField);if(!id)return JNI_FALSE;const char* value=e->GetStringUTFChars(id,nullptr);int player=!strcmp(value,"CX_PAD_PRESET1")?0:!strcmp(value,"CX_PAD_PRESET2")?1:-1;e->ReleaseStringUTFChars(id,value);e->DeleteLocalRef(id);if(player<0)return JNI_FALSE;
 int port=ports[player];if(!padConnected(port)){for(int n=0;n<4;n++)if(padConnected(n)&&padSelection(e,menu,1-player)!=n+1){port=n;break;}}
 jobject combo=padGetCombo(e,menu,player);e->CallVoidMethod(combo,padSetSel,port+1);e->DeleteLocalRef(combo);
 if(padSelection(e,menu,1-player)==port+1){combo=padGetCombo(e,menu,1-player);e->CallVoidMethod(combo,padSetSel,0);e->DeleteLocalRef(combo);padDisplaySelection(e,menu,1-player,0,true);}
 padDisplaySelection(e,menu,player,port+1,true);logf("controller preset: player=%d port=%d",player+1,port+1);return JNI_TRUE;
}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_ConfigureController(JNIEnv* e,jclass,jobject controller,jobject kb){
 if(!padAPI(e))return;int port=-1;if(kb&&e->GetIntField(kb,padDeviceField)==3)port=std::clamp((int)e->GetIntField(kb,padJoyNumberField),0,3);e->SetIntField(controller,padPortField,port);
}
static int padControllerPort(JNIEnv* e,jobject controller){if(!controller||!padAPI(e))return -1;return e->GetIntField(controller,padPortField);}
extern "C" JNIEXPORT jboolean JNICALL Java_CXSupport_PadOwnsLegacyInput(JNIEnv* e,jclass,jobject controller){return enabled&&padControllerPort(e,controller)>=0?JNI_TRUE:JNI_FALSE;}
extern "C" JNIEXPORT void JNICALL Java_CXSupport_InitializePadDefaults(JNIEnv* e,jclass){
 if(!enabled||!getState||GetPrivateProfileIntA("Gamepad","ProfileModeInitialized",0,ini)||!padAPI(e))return;
 int found[4],count=0;for(int n=0;n<4;n++)if(padConnected(n))found[count++]=n;if(!count)return;
 bool changed=false;for(int i=0;i<std::min(count,2);i++){jobject kb=padKbFor(e,i);if(!kb)continue;e->SetIntField(kb,padDeviceField,3);e->SetIntField(kb,padJoyNumberField,found[i]);ports[i]=found[i];e->DeleteLocalRef(kb);changed=true;logf("new-copy default controller: player=%d XInput=%d",i+1,found[i]+1);}
 if(changed){WritePrivateProfileStringA("Gamepad","ProfileModeInitialized","1",ini);e->CallStaticVoidMethod(sg,e->GetStaticMethodID(sg,"SaveAttrib","()V"));}error(e,"first controller setup");
}
static void padSaveModernPorts(JNIEnv* e){
 if(!padAPI(e))return;for(int i=0;i<2;i++){jobject kb=padKbFor(e,i);if(kb){e->SetIntField(kb,padDeviceField,3);e->SetIntField(kb,padJoyNumberField,ports[i]);e->DeleteLocalRef(kb);}}
 WritePrivateProfileStringA("Gamepad","ProfileModeInitialized","1",ini);e->CallStaticVoidMethod(sg,e->GetStaticMethodID(sg,"SaveAttrib","()V"));error(e,"modern controller port assignment");
}
static bool padCursorInverted(){return invertY!=0;}
