#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    typedef SOCKET socket_t;
    #define CLOSESOCKET closesocket
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    typedef int socket_t;
    #define CLOSESOCKET close
#endif

#define SERVER_IP "127.0.0.1"
#define SERVER_PORT 5000
#define BUFFER_SIZE 65536

void send_packet(socket_t sock, const char *packet) {
    char framed[BUFFER_SIZE];
    snprintf(framed, sizeof(framed), "%s\n", packet);
    send(sock, framed, (int)strlen(framed), 0);
    printf("[TX]: %s\n", packet);
}

int recv_packet(socket_t sock, char *out, int max_len) {
    int total = 0;
    char ch;
    while (total < max_len - 1) {
        int n = (int)recv(sock, &ch, 1, 0);
        if (n <= 0) return -1;
        if (ch == '\n') break;
        out[total++] = ch;
    }
    out[total] = '\0';
    return total;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <filename>\n", argv[0]);
        return 1;
    }
    const char *filename = argv[1];

#ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    socket_t sock = socket(AF_INET, SOCK_STREAM, 0);
    
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    
    server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);

    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        printf("Connection failed\n");
        CLOSESOCKET(sock);
        return 1;
    }
    
    char buffer[BUFFER_SIZE];
    
    send_packet(sock, "(SS,RFMP,v1.0,0)");
    recv_packet(sock, buffer, BUFFER_SIZE);
    printf("[RX]: %s\n", buffer);
    
    char command_packet[BUFFER_SIZE];
    snprintf(command_packet, sizeof(command_packet), "(CM, openRead, %s)", filename);
    send_packet(sock, command_packet);
    
    if (recv_packet(sock, buffer, BUFFER_SIZE) > 0) {
        if (strncmp(buffer, "(EE,", 4) == 0) {
            printf("Error: %s\n", buffer);
        } else if (strncmp(buffer, "(SC,", 4) == 0 || strncmp(buffer, "(DP,", 4) == 0) {
            char *contents = buffer + 4;
            size_t len = strlen(contents);
            if (len > 0 && contents[len - 1] == ')') {
                contents[len - 1] = '\0';
            }
            printf("File contents:\n%s\n", contents);
        }
    }

    send_packet(sock, "(End)");

    CLOSESOCKET(sock);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}