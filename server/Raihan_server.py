"""
server.py - Multithreaded RFMP (Remote File Management Protocol) server

Uses crypto.py (RSA / AES / Caesar) and command_handler.py (folder/file commands).
Run:  python server.py        (needs: pip install pycryptodome)

Error codes:  E01 unknown command   E02 not found   E03 already exists   E04 other failure
"""

import socket
import threading

import command_handler
import crypto

HOST = "127.0.0.1"
PORT = 5000
BUFFER = 1024 * 1024    # max bytes read per packet


def send(conn, packet):
    """Send one packet (a string) to the client."""
    print("TX ->", packet[:80])
    # Add a newline so the C client knows the packet is finished
    conn.sendall((packet + "\n").encode("utf-8"))


def to_packet(result):
    """command_handler returns ("SC", msg) or ("EE", code, desc) - turn it into a packet."""
    if result[0] == "SC":
        return f"(SC,{result[1]})"
    return f"(EE,{result[1]},{result[2]})"


def encrypt(text, alg, key):
    """Encrypt file contents with the session key (alg is None when not secured)."""
    if alg == "AES":
        return crypto.aes_encrypt(text, key)
    if alg == "CAESAR":
        return crypto.caesar_encrypt(text, key)
    return text


def decrypt(text, alg, key):
    if alg == "AES":
        return crypto.aes_decrypt(text, key)
    if alg == "CAESAR":
        return crypto.caesar_decrypt(text, key)
    return text


def setup_phase(conn):
    """
    Start-Packet -> Confirm-Connection-Packet (and Encryption-Packet if secured).
    Returns (algorithm, session_key), or None if the setup failed.
    """
    packet = conn.recv(BUFFER).decode("utf-8").strip()
    print("RX <-", packet[:80])
    fields = [f.strip() for f in packet[1:-1].split(",")]    # (SS,RFMP,v1.0,0) -> list

    if len(fields) != 4 or fields[0] != "SS" or fields[1] != "RFMP":
        send(conn, "(EE,E04,Expected Start-Packet (SS,RFMP,v1.0,0|1))")
        return None

    if fields[3] == "0":                    # not secured
        send(conn, "(CC)")
        return None, None

    # Secured: make an RSA keypair and send the public key to the client
    public_pem, private_pem = crypto.generate_rsa_keypair()
    send(conn, f"(CC,{public_pem})")

    packet = conn.recv(BUFFER).decode("utf-8").strip()
    print("RX <-", packet[:80])
    try:
        alg, enc_key, username, client_pub = crypto.parse_encryption_packet(packet)
        session_key = crypto.rsa_decrypt_session_key(enc_key, private_pem)   # our private key unlocks it
        alg = alg.upper()
        if alg == "CAESAR":
            session_key = int(session_key.decode("utf-8"))                   # Caesar key = shift number
        elif alg != "AES":
            raise ValueError("unsupported algorithm " + alg)
    except Exception as e:
        send(conn, f"(EE,E04,Encryption setup failed: {e})")
        return None

    print(f"Secured session with {username} using {alg}")
    send(conn, "(SC,Secure session established)")
    return alg, session_key


def handle_client(conn, addr):
    """Runs in its own thread, one per client."""
    print("Connected:", addr)
    write_file = None                       # file handle after an openWrite

    try:
        setup = setup_phase(conn)
        if setup is None:
            return
        alg, key = setup

        # ---------- operation phase ----------
        while True:
            data = conn.recv(BUFFER)
            if not data:                    # client disconnected
                break
            packet = data.decode("utf-8").strip()
            print("RX <-", packet[:80])

            inner = packet[1:-1]            # remove the outer ( )
            ptype = inner.split(",", 1)[0].strip()

            if ptype == "End":              # ---------- closing phase ----------
                send(conn, "(SC,Session closed)")
                break

            elif ptype == "CM":             # (CM,mode,arguments)
                if write_file:              # a new command ends the previous openWrite
                    command_handler.close_file(write_file)
                    write_file = None

                parts = inner.split(",", 2)
                mode = parts[1].strip().lower() if len(parts) > 1 else ""
                args = parts[2].strip() if len(parts) > 2 else ""

                if mode == "prompt":        # e.g. "mkdir docs", "ren a b"
                    command, _, rest = args.partition(" ")
                    command = command.lower()
                    if command == "rd":
                        command = "rmdir"
                    send(conn, to_packet(command_handler.execute_prompt_command(command, rest.strip())))

                elif mode == "openread":    # send the file back in a Data Packet
                    result = command_handler.open_read(args)
                    if result[0] == "SC":
                        send(conn, f"(DP,{encrypt(result[1], alg, key)})")
                    else:
                        send(conn, to_packet(result))

                elif mode == "openwrite":   # keep the file open for the Data Packets that follow
                    result = command_handler.open_write(args)
                    if result[0] == "SC":
                        write_file = result[1]
                        send(conn, f"(SC,Ready to receive data for '{args}')")
                    else:
                        send(conn, to_packet(result))

                else:
                    send(conn, f"(EE,E01,Unknown command type: {mode})")

            elif ptype == "DP":             # (DP,text) - decrypt and write to the open file
                if write_file is None:
                    send(conn, "(EE,E04,No file open for writing - send openWrite first)")
                    continue
                text = inner.split(",", 1)[1] if "," in inner else ""
                try:
                    text = decrypt(text, alg, key)
                except Exception:
                    send(conn, "(EE,E04,Decryption failed)")
                    continue
                send(conn, to_packet(command_handler.write_data(write_file, text)))

            else:
                send(conn, f"(EE,E01,Unknown packet type: {ptype})")

    except OSError as e:
        print("Connection error:", e)
    finally:
        if write_file:
            command_handler.close_file(write_file)
        conn.close()
        print("Disconnected:", addr)


def start_server(host=HOST, port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(10)
    print(f"RFMP server listening on {host}:{port}")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
