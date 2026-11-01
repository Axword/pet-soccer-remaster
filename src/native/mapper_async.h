// Process discovery is Windows-only worker work; never touches JNI or OpenGL.
// Included after logf/foreground/key/click, replacing the old hasMapper helper.
static volatile LONG cxMapperCached=-1,cxMapperBusy=0;
static bool cxMapperPinAttempted=false;
static HMODULE cxMapperLifetime=nullptr;

static int cxMapperScanProcesses(){
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
 if(snapshot==INVALID_HANDLE_VALUE)return -1;
 PROCESSENTRY32W process={sizeof(process)};
 if(!Process32FirstW(snapshot,&process)){CloseHandle(snapshot);return -1;}
 int found=0;
 do{
  if(_wcsicmp(process.szExeFile,L"antimicrox.exe")==0||_wcsicmp(process.szExeFile,L"antimicrox")==0){found=1;break;}
 }while(Process32NextW(snapshot,&process));
 CloseHandle(snapshot);return found;
}
static DWORD WINAPI cxMapperWorker(LPVOID){
 int found=cxMapperScanProcesses();
 if(found>=0)InterlockedExchange(&cxMapperCached,found);
 InterlockedExchange(&cxMapperBusy,0);return 0;
}
static bool cxMapperPoll(DWORD now){
 // A queued Windows threadpool callback must not execute from an unloaded DLL.
 // This bridge is process-lifetime already; pin exactly once before dispatch.
 if(!cxMapperPinAttempted){
  cxMapperPinAttempted=true;
  GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                    reinterpret_cast<LPCSTR>(&cxMapperWorker),&cxMapperLifetime);
 }
 if(cxMapperLifetime&&(!mapperCheck||now-mapperCheck>=2000)){
  mapperCheck=now;
  if(InterlockedCompareExchange(&cxMapperBusy,1,0)==0){
   if(!QueueUserWorkItem(cxMapperWorker,nullptr,WT_EXECUTEDEFAULT))InterlockedExchange(&cxMapperBusy,0);
  }
 }
 LONG state=InterlockedCompareExchange(&cxMapperCached,0,0);
 // While initial discovery is pending, avoid injecting duplicate menu input.
 // Native gameplay routing remains independent of this mapper-menu flag.
 return state<0?true:state!=0;
}
