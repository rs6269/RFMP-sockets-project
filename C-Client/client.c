/*
 * RFMP C Client
 * -------------
 * Unencrypted C client 
 * it only handles the setup phase without security 
 * and only runs the openRead command
 *
 * Usage:   ./client <filename>
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
    /*
    * Windows uses Winsock instead of the standard POSIX headers.
    * Using this #ifdef block so the code compiles smoothly on both 
    * Windows and Linux without having to change anything.
    */
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

#define SERVER_IP   "127.0.0.1"   // Testing locally
#define SERVER_PORT 5000          // Matches the Python server port
#define BUFFER_SIZE 65536         // 64KB to handle large file reads

/* 
 * TCP doesn't have a concept of "messages", it's just a raw byte stream. 
 * Attaching a '\n' to the end of every packet so the server actually 
 * knows when the packet finishes. 
 */
void send_packet(socket_t sock, const char *packet) {
    char framed[BUFFER_SIZE];
    snprintf(framed, sizeof(framed), "%s\n", packet);   
    send(sock, framed, (int)strlen(framed), 0);
    printf("[TX]: %s\n", packet);
}

/* 
 * Reads exactly one packet. It grabs one byte at a time until it hits the '\n'. 
 * If a fixed recv() buffer is used, multiple packets could get glued 
 * together, so this prevents that.
 */
int recv_packet(socket_t sock, char *out, int max_len) {
    int total = 0;
    char ch;
    while (total < max_len - 1) {
        int n = (int)recv(sock, &ch, 1, 0);   
        if (n <= 0) return -1;                // Connection dropped  
        if (ch == '\n') break;                // Found the end of the packet
        out[total++] = ch;
    }
    out[total] = '\0';   // Null-terminate so C treats it as a string
    return total;
}

int main(int argc, char *argv[]) {
    // Need at least 2 args since argv[0] is just the program name
    if (argc < 2) {
        printf("Usage: %s <filename>\n", argv[0]);
        return 1;
    }
    const char *filename = argv[1];

#ifdef _WIN32
    // Windows requires WSAStartup to initialize sockets. Linux doesn't.
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    // IPv4, TCP socket
    socket_t sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));   // Clear garbage bytes
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);       

    // Convert IP string to binary. Using inet_addr to avoid MinGW compiler errors.
    server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);   

    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        printf("Connection failed\n");
        CLOSESOCKET(sock);
        return 1;
    }

    char buffer[BUFFER_SIZE];

    // --- Setup Phase --- 
    // The C client isn't supposed to have encryption, so the security flag is 0.
    // Server should just reply with a plain (CC).
    send_packet(sock, "(SS,RFMP,v1.0,0)");
    recv_packet(sock, buffer, BUFFER_SIZE);
    printf("[RX]: %s\n", buffer);

    // --- Operation Phase ---
    // So it has to be (CM, openRead, <file>), not (CM, prompt, openRead).
    char command_packet[BUFFER_SIZE];
    snprintf(command_packet, sizeof(command_packet), "(CM, openRead, %s)", filename);
    send_packet(sock, command_packet);

    if (recv_packet(sock, buffer, BUFFER_SIZE) > 0) {
        if (strncmp(buffer, "(EE,", 4) == 0) {
            // Server threw an error 
            printf("Error: %s\n", buffer);
        } else if (strncmp(buffer, "(SC,", 4) == 0 || strncmp(buffer, "(DP,", 4) == 0) {
            // Checking for both SC and DP just in case the server wraps the 
            // file contents differently.
            char *contents = buffer + 4;              // Skip the 4-char prefix
            size_t len = strlen(contents);
            if (len > 0 && contents[len - 1] == ')') { 
                contents[len - 1] = '\0';             // Strip the trailing parenthesis
            }
            printf("File contents:\n%s\n", contents);
        }
    }

    // --- Closing Phase ---
    send_packet(sock, "(End)");

    CLOSESOCKET(sock);
#ifdef _WIN32
    WSACleanup();   
#endif
    return 0;
}