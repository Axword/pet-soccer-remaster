#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#include <windows.h>
#include <tlhelp32.h>
#include <filesystem>
#include <string>
#include <vector>
#pragma comment(lib,"Ws2_32.lib")

// Local prototype convenience launcher. No firewall or system settings changes.
static bool probeWait(SOCKET s,bool writing,DWORD started,DWORD timeoutMs) {
    DWORD elapsed=GetTickCount()-started;
    if(elapsed>=timeoutMs)return false;
    DWORD remaining=timeoutMs-elapsed;
    timeval timeout={static_cast<long>(remaining/1000),static_cast<long>((remaining%1000)*1000)};
    fd_set ready,errors;FD_ZERO(&ready);FD_SET(s,&ready);FD_ZERO(&errors);FD_SET(s,&errors);
    return select(0,writing?nullptr:&ready,writing?&ready:nullptr,&errors,&timeout)>0
        &&FD_ISSET(s,&ready)&&!FD_ISSET(s,&errors);
}
static bool probeTransfer(SOCKET s,char* bytes,int count,bool writing,DWORD started,DWORD timeoutMs) {
    int offset=0;
    while(offset<count) {
        if(!probeWait(s,writing,started,timeoutMs))return false;
        int got=writing?send(s,bytes+offset,count-offset,0):recv(s,bytes+offset,count-offset,0);
        if(got==SOCKET_ERROR) {
            if(WSAGetLastError()==WSAEWOULDBLOCK)continue;
            return false;
        }
        if(got<=0)return false;
        offset+=got;
    }
    return true;
}
static unsigned readBigEndian(const unsigned char* data) {
    return (static_cast<unsigned>(data[0])<<24)|(static_cast<unsigned>(data[1])<<16)
        |(static_cast<unsigned>(data[2])<<8)|data[3];
}
// A reachable unrelated TCP service must never count as this prototype's broker.
// Alternate port and one total deadline make this independently testable.
static bool brokerReady(unsigned short port=27888,DWORD timeoutMs=400) {
    DWORD started=GetTickCount();
    SOCKET s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s==INVALID_SOCKET)return false;
    u_long mode=1;
    if(ioctlsocket(s,FIONBIO,&mode)!=0){closesocket(s);return false;}
    sockaddr_in address={};address.sin_family=AF_INET;address.sin_port=htons(port);
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    bool ok=connect(s,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0;
    if(!ok&&WSAGetLastError()==WSAEWOULDBLOCK) {
        if(probeWait(s,true,started,timeoutMs)) {
            int error=1,size=sizeof(error);
            if(getsockopt(s,SOL_SOCKET,SO_ERROR,reinterpret_cast<char*>(&error),&size)==0)ok=error==0;
        }
    }
    if(ok) {
        std::vector<char> hello(4,0);hello.push_back(1);hello.push_back(0);hello.push_back(1);
        const std::string fields[]={"LauncherProbe","GMWL-6fbcaedb-online5"};
        for(const auto& field:fields) {
            hello.push_back(static_cast<char>((field.size()>>8)&255));
            hello.push_back(static_cast<char>(field.size()&255));
            hello.insert(hello.end(),field.begin(),field.end());
        }
        unsigned length=static_cast<unsigned>(hello.size()-4);
        for(int i=0;i<4;i++)hello[i]=static_cast<char>((length>>(24-i*8))&255);
        ok=probeTransfer(s,hello.data(),static_cast<int>(hello.size()),true,started,timeoutMs);
        unsigned char header[4]={},welcome[5]={};
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(header),4,false,started,timeoutMs);
        // Reject zero/oversized/truncated frames before reading/allocating a body.
        if(ok)ok=header[0]==0&&header[1]==0&&header[2]==0&&header[3]==5;
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(welcome),5,false,started,timeoutMs);
        if(ok)ok=welcome[0]==2&&(welcome[1]&128)==0
            &&(welcome[1]!=0||welcome[2]!=0||welcome[3]!=0||welcome[4]!=0);
        // WELCOME alone is also emitted by pre-ranking brokers. Require the
        // current statistics capability before launching a new client.
        char request[]={0,0,0,1,20};
        if(ok)ok=probeTransfer(s,request,5,true,started,timeoutMs);
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(header),4,false,started,timeoutMs);
        unsigned size=ok?readBigEndian(header):0;
        if(ok)ok=size>=32&&size<=79;
        unsigned char stats[79]={};
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(stats),static_cast<int>(size),false,started,timeoutMs);
        if(ok) {
            unsigned nickSize=(static_cast<unsigned>(stats[1])<<8)|stats[2];
            ok=stats[0]==21&&nickSize>=1&&nickSize<=48&&size==31+nickSize;
            for(unsigned i=0;ok&&i<nickSize;i++)ok=stats[3+i]>=32&&stats[3+i]<=126;
            unsigned values[7]={};
            for(int i=0;ok&&i<7;i++) {
                values[i]=readBigEndian(stats+3+nickSize+i*4);
                ok=values[i]<=0x7fffffff;
            }
            if(ok) {
                unsigned long long games=static_cast<unsigned long long>(values[1])+values[2]+values[3];
                unsigned long long points=3ULL*values[1]+values[2];
                unsigned rate=games?static_cast<unsigned>(10000ULL*values[1]/games):0;
                ok=games==values[4]&&points==values[5]&&rate==values[6];
            }
        }
        char capabilities[]={0,0,0,1,26};
        if(ok)ok=probeTransfer(s,capabilities,5,true,started,timeoutMs);
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(header),4,false,started,timeoutMs);
        if(ok)ok=readBigEndian(header)==5;
        unsigned char supported[5]={};
        if(ok)ok=probeTransfer(s,reinterpret_cast<char*>(supported),5,false,started,timeoutMs);
        if(ok)ok=supported[0]==27&&(supported[1]&128)==0&&(readBigEndian(supported+1)&7)==7;
    }
    shutdown(s,SD_BOTH);
    closesocket(s);return ok;
}
#ifndef PETSOCCER_LAUNCHER_PROBE_ONLY
static std::wstring resolvedImagePath(const std::filesystem::path& path) {
    HANDLE file=CreateFileW(path.c_str(),0,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
        nullptr,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS,nullptr);
    if(file!=INVALID_HANDLE_VALUE) {
        wchar_t name[32768];DWORD size=GetFinalPathNameByHandleW(file,name,32768,FILE_NAME_NORMALIZED);
        CloseHandle(file);
        if(size&&size<32768)return std::wstring(name,size);
    }
    return std::filesystem::absolute(path).lexically_normal().wstring();
}
static bool sameImagePath(const std::filesystem::path& actual,const std::wstring& expected) {
    std::wstring normalized=resolvedImagePath(actual);
    return CompareStringOrdinal(normalized.c_str(),-1,expected.c_str(),-1,TRUE)==CSTR_EQUAL;
}
// The bootstrap is short-lived; the actual engine continues as PetSoccer.bum.
// Restrict detection to this installation, not every similarly named process.
static bool gameRunning(const std::filesystem::path& gameRoot,bool engineOnly=false) {
    const std::wstring bootstrap=resolvedImagePath(gameRoot/L"PetSoccer.exe");
    const std::wstring engine=resolvedImagePath(gameRoot/L"PetSoccer.bum");
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    if(snapshot==INVALID_HANDLE_VALUE)return false;
    PROCESSENTRY32W entry={};entry.dwSize=sizeof(entry);bool found=false;
    for(BOOL more=Process32FirstW(snapshot,&entry);more;more=Process32NextW(snapshot,&entry)) {
        bool isEngine=_wcsicmp(entry.szExeFile,L"PetSoccer.bum")==0;
        bool isBootstrap=!engineOnly&&_wcsicmp(entry.szExeFile,L"PetSoccer.exe")==0;
        if(!isEngine&&!isBootstrap)continue;
        HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,entry.th32ProcessID);
        if(!process)continue;
        wchar_t image[32768];DWORD size=32768;
        bool queried=QueryFullProcessImageNameW(process,0,image,&size)!=FALSE;
        CloseHandle(process);
        if(queried&&sameImagePath(std::filesystem::path(std::wstring(image,size)),isEngine?engine:bootstrap)) {
            found=true;break;
        }
    }
    CloseHandle(snapshot);return found;
}
class StartupGuard {
    HANDLE mutex=nullptr;bool owned=false;
public:
    explicit StartupGuard(const std::filesystem::path& game) {
        // A directory identity covers shortcuts/junctions while keeping two
        // installs independent even when their executable files are hardlinks.
        HANDLE file=CreateFileW(game.parent_path().c_str(),0,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
            nullptr,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS,nullptr);
        BY_HANDLE_FILE_INFORMATION info={};
        if(file==INVALID_HANDLE_VALUE)return;
        bool valid=GetFileInformationByHandle(file,&info)!=FALSE;CloseHandle(file);
        if(!valid)return;
        wchar_t name[128];swprintf_s(name,L"Local\\PetSoccerOnlineLaunch-%08lx-%08lx-%08lx",
            info.dwVolumeSerialNumber,info.nFileIndexHigh,info.nFileIndexLow);
        mutex=CreateMutexW(nullptr,FALSE,name);
        if(mutex) {
            DWORD wait=WaitForSingleObject(mutex,0);
            owned=wait==WAIT_OBJECT_0||wait==WAIT_ABANDONED;
        }
    }
    ~StartupGuard(){if(owned)ReleaseMutex(mutex);if(mutex)CloseHandle(mutex);}
    bool acquired()const{return owned;}
};
static bool spawn(const std::filesystem::path& executable,std::wstring args,
                  const std::filesystem::path& cwd,bool hidden,HANDLE log=nullptr,HANDLE* retainedProcess=nullptr) {
    std::wstring command=L"\""+executable.wstring()+L"\" "+args;
    std::vector<wchar_t> buffer(command.begin(),command.end());buffer.push_back(0);
    STARTUPINFOW start={};start.cb=sizeof(start);PROCESS_INFORMATION process={};
    if(log&&log!=INVALID_HANDLE_VALUE) {
        start.dwFlags=STARTF_USESTDHANDLES;start.hStdOutput=log;start.hStdError=log;
        start.hStdInput=GetStdHandle(STD_INPUT_HANDLE);
    }
    bool ok=CreateProcessW(executable.c_str(),buffer.data(),nullptr,nullptr,log!=nullptr,
        hidden?CREATE_NO_WINDOW:0,nullptr,cwd.c_str(),&start,&process)!=FALSE;
    if(ok){CloseHandle(process.hThread);if(retainedProcess)*retainedProcess=process.hProcess;else CloseHandle(process.hProcess);}
    return ok;
}
static void waitForEngine(const std::filesystem::path& gameRoot,HANDLE bootstrap,DWORD timeoutMs=15000) {
    DWORD started=GetTickCount();
    // Keep the startup lock across bootstrap -> engine handoff. Afterwards each
    // fresh launcher checks the engine path, so no permanent helper is needed.
    while(GetTickCount()-started<timeoutMs) {
        if(gameRunning(gameRoot,true))break;
        Sleep(100);
    }
    CloseHandle(bootstrap);
}
static bool writableDirectory(const std::filesystem::path& path) {
    std::error_code failure;std::filesystem::create_directories(path,failure);
    if(failure||!std::filesystem::is_directory(path))return false;
    auto test=path/(L".write-check-"+std::to_wstring(GetCurrentProcessId()));
    HANDLE file=CreateFileW(test.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,
        FILE_ATTRIBUTE_TEMPORARY|FILE_FLAG_DELETE_ON_CLOSE,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;CloseHandle(file);return true;
}
#ifndef PETSOCCER_LAUNCHER_GUARD_TEST
static int launchPortable(const std::filesystem::path& root,bool remote) {
    auto gameRoot=root;auto game=gameRoot/L"PetSoccer.exe";
    if(!std::filesystem::is_regular_file(game)) {
        MessageBoxW(nullptr,L"Nie znaleziono PetSoccer.exe obok launchera. Uruchom pelna instalacje moda.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);return 2;
    }
    StartupGuard guard(game);
    if(!guard.acquired()||gameRunning(gameRoot))return 0;
    if(!remote) {
        WSADATA data={};if(WSAStartup(MAKEWORD(2,2),&data)!=0) {
            MessageBoxW(nullptr,L"Nie udalo sie uruchomic obslugi sieci Windows.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);return 3;
        }
        if(!brokerReady()) {
            auto python=root/L"online"/L"runtime"/L"python.exe";
            auto broker=root/L"online"/L"broker.py";
            auto logs=root/L"online"/L"logs",database=root/L"online"/L"data";
            if(!std::filesystem::is_regular_file(python)||!std::filesystem::is_regular_file(broker)) {
                MessageBoxW(nullptr,L"Brakuje skladnikow Online. Zainstaluj ponownie pelna paczke moda; Blender ani osobny Python nie sa potrzebne.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);WSACleanup();return 4;
            }
            if(!writableDirectory(logs)||!writableDirectory(database)) {
                MessageBoxW(nullptr,L"Brak prawa zapisu w online/data lub online/logs. Zainstaluj kopie moda w swoim folderze uzytkownika.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);WSACleanup();return 8;
            }
            auto logPath=logs/L"broker-local.log";
            SECURITY_ATTRIBUTES security={sizeof(security),nullptr,TRUE};
            HANDLE log=CreateFileW(logPath.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
            if(log==INVALID_HANDLE_VALUE) {
                MessageBoxW(nullptr,L"Nie mozna zapisac dziennika online/logs/broker-local.log.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);WSACleanup();return 9;
            }
            std::wstring args=L"-I -u \""+broker.wstring()+L"\" --bind 127.0.0.1 --port 27888 --db \""+(database/L"leaderboard.sqlite3").wstring()+L"\"";
            bool started=spawn(python,args,root,true,log);CloseHandle(log);
            bool ready=false;DWORD begin=GetTickCount();
            while(started&&GetTickCount()-begin<15000) {
                DWORD remaining=15000-(GetTickCount()-begin);
                if(brokerReady(27888,std::min<DWORD>(400,remaining))){ready=true;break;}
                if(GetTickCount()-begin<15000)Sleep(100);
            }
            if(!ready) {
                MessageBoxW(nullptr,L"Lokalne lobby nie odpowiada albo port27888 zajmuje starszy/inny serwer. Zamknij poprzednie lobby i sprobuj ponownie. Szczegoly: online/logs/broker-local.log. Do gry na obcym serwerze mozesz uzyc skrotu Online - polacz ze swoim serwerem.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);WSACleanup();return 5;
            }
        }
        WSACleanup();
    }
    HANDLE bootstrap=nullptr;
    if(!spawn(game,L"",gameRoot,false,nullptr,&bootstrap)) {
        MessageBoxW(nullptr,L"Nie udalo sie uruchomic Pet Soccer.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);return 6;
    }
    waitForEngine(gameRoot,bootstrap,15000);return 0;
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR arguments,int) {
    try {
        std::wstring option=arguments?arguments:L"";
        auto begin=option.find_first_not_of(L" \t\r\n"),end=option.find_last_not_of(L" \t\r\n");
        option=begin==std::wstring::npos?L"":option.substr(begin,end-begin+1);
        if(!option.empty()&&option!=L"--remote") {
            MessageBoxW(nullptr,L"Nieznany parametr launchera. Dostepne: --remote (bez lokalnego serwera).",L"Pet Soccer Online",MB_OK|MB_ICONERROR);return 7;
        }
        wchar_t own[32768];DWORD count=GetModuleFileNameW(nullptr,own,32768);if(!count||count>=32768)return 1;
        return launchPortable(std::filesystem::path(own).parent_path(),option==L"--remote");
    } catch(const std::exception&) {
        MessageBoxW(nullptr,L"Nie mozna odczytac plikow lub uruchomic Online. Sprawdz folder instalacji i uprawnienia.",L"Pet Soccer Online",MB_OK|MB_ICONERROR);return 10;
    }
}
#endif
#endif
