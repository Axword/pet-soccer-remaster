#define PETSOCCER_LAUNCHER_PROBE_ONLY
#include "../src/online_launcher.cpp"
#include <cstdlib>
int main(int argc,char** argv) {
    if(argc!=2)return 2;int port=std::atoi(argv[1]);
    if(port<1||port>65535||port==27888||port==27889)return 3;
    WSADATA data={};if(WSAStartup(MAKEWORD(2,2),&data)!=0)return 4;
    bool ready=brokerReady(static_cast<unsigned short>(port),400);WSACleanup();return ready?0:1;
}
