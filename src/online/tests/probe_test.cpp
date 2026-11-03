#define PETSOCCER_LAUNCHER_PROBE_ONLY
#include "../src/online_launcher.cpp"
#include <cstdlib>
#include <cstdio>
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    int port=std::atoi(argv[1]);
    if(port<1||port>65535||port==27888)return 3;
    WSADATA data={};if(WSAStartup(MAKEWORD(2,2),&data)!=0)return 4;
    bool ready=brokerReady(static_cast<unsigned short>(port),200);
    WSACleanup();
    std::puts(ready?"READY":"NOT_READY");
    return ready?0:1;
}
