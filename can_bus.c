#include "can_bus.h"

#ifdef _WIN32
#include <winsock2.h>
#else
#include <arpa/inet.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int SOCKET;
#endif

static SOCKET sock;

bool can_open(void) {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
    struct sockaddr_in hub = { .sin_family = AF_INET, .sin_port = htons(47100) };
    hub.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    return connect(sock, (struct sockaddr *)&hub, sizeof hub) == 0
        && send(sock, "HELO", 4, 0) == 4; // any packet registers this node at the hub
}

void can_send(const CanFrame *frame) {
    send(sock, (const char *)frame, sizeof *frame, 0);
}

bool can_receive(CanFrame *frame, int timeout_ms) {
    fd_set readable;
    FD_ZERO(&readable);
    FD_SET(sock, &readable);
    struct timeval timeout = { .tv_usec = timeout_ms * 1000 };
    return select(sock + 1, &readable, NULL, NULL, &timeout) > 0
        && recv(sock, (char *)frame, sizeof *frame, 0) == sizeof *frame;
}
