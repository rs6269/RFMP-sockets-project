#!/usr/bin/env python3
"""
RFMP Server
----------------
"""

import socket
import struct
import threading
from pathlib import Path

import command_handler


HOST = "0.0.0.0"
PORT = 5000
MAX_PACKET = 1024 * 1024

SINGLE_PATH_COMMANDS = {
    "mkdir": "mkdir",
    "rmdir": "rmdir",
    "rd": "rmdir",
    "del": "del",
    "type": "type",
}
TWO_PATH_COMMANDS = {"ren", "move", "copy"}

# SERVER SOCKET LOOP

def start_server(host=HOST, port=PORT):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(10)
    print(f"RFMP Server listening on {host}:{port}")
    print("Standalone mode: encryption OFF, openRead ON")

    try:
        while True:
            client_socket, address = server_socket.accept()
            threading.Thread(target=client_worker, args=(client_socket, address), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server_socket.close()