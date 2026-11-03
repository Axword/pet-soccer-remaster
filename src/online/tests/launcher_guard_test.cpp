#define PETSOCCER_LAUNCHER_GUARD_TEST
#include "../src/online_launcher.cpp"
#include <cstdio>
#include <cstdlib>

static void mark(const std::filesystem::path& path) {
    HANDLE file=CreateFileW(path.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,
        nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)ExitProcess(8);
    DWORD written=0;const char text[]="START\n";
    WriteFile(file,text,sizeof(text)-1,&written,nullptr);CloseHandle(file);
}
int wmain(int argc,wchar_t** argv) {
    if(argc>=3&&wcscmp(argv[1],L"--worker")==0){Sleep(static_cast<DWORD>(_wtoi(argv[2])));return 0;}
    if(argc==4&&wcscmp(argv[1],L"--bootstrap")==0) {
        Sleep(static_cast<DWORD>(_wtoi(argv[3])));
        return spawn(argv[2],L"--worker 2500",std::filesystem::path(argv[2]).parent_path(),true)?0:4;
    }
    if(argc==3&&wcscmp(argv[1],L"--check")==0) {
        bool running=gameRunning(argv[2]);std::puts(running?"RUNNING":"CLEAR");return running?10:0;
    }
    if(argc==4&&wcscmp(argv[1],L"--try")==0) {
        std::filesystem::path root=argv[2];StartupGuard guard(root/L"PetSoccer.exe");
        if(!guard.acquired()||gameRunning(root)){std::puts("SKIP");return 0;}
        mark(argv[3]);HANDLE process=nullptr;
        std::wstring args=L"--bootstrap \""+(root/L"PetSoccer.bum").wstring()+L"\" 700";
        if(!spawn(root/L"PetSoccer.exe",args,root,true,nullptr,&process))return 5;
        waitForEngine(root,process,4000);std::puts("STARTED");return 0;
    }
    return 2;
}
