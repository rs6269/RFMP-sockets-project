"""
server.py - Multithreaded RFMP (Remote File Management Protocol) server

Uses crypto.py (RSA / AES / Caesar) and command_handler.py (folder/file commands).
Run:  python Raihan_server.py        (needs: pip install pycryptodome)

Error codes:  E01 unknown command   E02 not found   E03 already exists   E04 other failure
"""

import socket                                   # Python's built-in TCP socket library for network communication
import threading                                # lets us run one thread per client so many clients work at once

import command_handler                          # our module that actually performs mkdir/rmdir/ren/read/write on disk
import crypto                                   # our module holding RSA, AES and Caesar encryption helpers

HOST = "127.0.0.1"                              # localhost: only clients on this same machine can connect
PORT = 5000                                     # the TCP port the server listens on (client must use the same one)
BUFFER = 1024 * 1024                            # max bytes read per recv() call (1 MB), enough for large file packets


def send(conn, packet):
    """Send one packet (a string) to the client."""
    print("TX ->", packet[:80])                 # log the outgoing packet, trimmed to 80 chars so big files don't flood the console
    # Add a newline so the C client knows the packet is finished
    conn.sendall((packet + "\n").encode("utf-8"))   # append the newline delimiter, convert to bytes, and send everything


def to_packet(result):
    """command_handler returns ("SC", msg) or ("EE", code, desc) - turn it into a packet."""
    if result[0] == "SC":                       # "SC" means the command succeeded
        return f"(SC,{result[1]})"              # wrap the success message in an RFMP Success packet
    return f"(EE,{result[1]},{result[2]})"      # otherwise wrap error code + description in an RFMP Error packet


def encrypt(text, alg, key):
    """Encrypt file contents with the session key (alg is None when not secured)."""
    if alg == "AES":                            # the client negotiated AES for this session
        return crypto.aes_encrypt(text, key)    # encrypt the text with the AES session key
    if alg == "CAESAR":                         # the client negotiated Caesar cipher for this session
        return crypto.caesar_encrypt(text, key) # shift the text's characters by the Caesar key
    return text                                 # unsecured session: send the text as-is, no encryption


def decrypt(text, alg, key):
    if alg == "AES":                            # session uses AES
        return crypto.aes_decrypt(text, key)    # turn the encrypted text back into plain text with the AES key
    if alg == "CAESAR":                         # session uses Caesar cipher
        return crypto.caesar_decrypt(text, key) # reverse the Caesar shift to recover the original text
    return text                                 # unsecured session: data is already plain text


def setup_phase(conn):
    """
    Start-Packet -> Confirm-Connection-Packet (and Encryption-Packet if secured).
    Returns (algorithm, session_key), or None if the setup failed.
    """
    packet = conn.recv(BUFFER).decode("utf-8").strip()      # wait for the client's first packet and clean it up
    print("RX <-", packet[:80])                             # log the incoming packet
    fields = [f.strip() for f in packet[1:-1].split(",")]    # (SS,RFMP,v1.0,0) -> drop the brackets, split on commas -> list

    if len(fields) != 4 or fields[0] != "SS" or fields[1] != "RFMP":    # must be exactly: SS, RFMP, version, secure-flag
        send(conn, "(EE,E04,Expected Start-Packet (SS,RFMP,v1.0,0|1))") # tell the client what the correct format is
        return None                             # handshake failed, so the caller will end this connection

    if fields[3] == "0":                        # secure flag 0 = client wants an unencrypted session
        send(conn, "(CC)")                      # send a plain Confirm-Connection packet, no key needed
        return None, None                       # no algorithm and no key (this is a tuple, so setup still counts as success)

    # Secured: make an RSA keypair and send the public key to the client
    public_pem, private_pem = crypto.generate_rsa_keypair() # create a fresh RSA pair just for this client
    send(conn, f"(CC,{public_pem})")            # confirm the connection and hand over the public key (private stays secret)

    packet = conn.recv(BUFFER).decode("utf-8").strip()      # wait for the Encryption-Packet containing the client's session key
    print("RX <-", packet[:80])                 # log the incoming packet
    try:
        alg, enc_key, username, client_pub = crypto.parse_encryption_packet(packet)  # pull algorithm, encrypted key, username, client public key out of the packet
        session_key = crypto.rsa_decrypt_session_key(enc_key, private_pem)   # our private key unlocks it
        alg = alg.upper()                       # normalise the name so "aes" / "Aes" / "AES" all match
        if alg == "CAESAR":                     # Caesar's key is just a number, not raw bytes
            session_key = int(session_key.decode("utf-8"))                   # Caesar key = shift number
        elif alg != "AES":                      # not Caesar and not AES means we don't support it
            raise ValueError("unsupported algorithm " + alg)    # jump to the except block below
    except Exception as e:                      # catches bad packet format, failed RSA decryption, bad key, etc.
        send(conn, f"(EE,E04,Encryption setup failed: {e})")    # tell the client why the secure setup failed
        return None                             # handshake failed, caller will close the connection

    print(f"Secured session with {username} using {alg}")       # server-side log of who connected and which cipher
    send(conn, "(SC,Secure session established)")               # tell the client encryption is ready to use
    return alg, session_key                     # give the caller the cipher name and key for the rest of the session


def handle_client(conn, addr):
    """Runs in its own thread, one per client."""
    print("Connected:", addr)                   # log the client's IP and port
    write_file = None                           # file handle after an openWrite (None = no file currently open)

    try:
        setup = setup_phase(conn)               # run the handshake (secure or unsecured)
        if setup is None:                       # handshake failed
            return                              # leave; the finally block below still closes the socket
        alg, key = setup                        # unpack the negotiated algorithm and session key

        # ---------- operation phase ----------
        while True:                             # keep serving commands until the client ends the session
            data = conn.recv(BUFFER)            # block until the client sends the next packet
            if not data:                        # empty bytes means the client closed the connection
                break                           # stop the loop and clean up
            packet = data.decode("utf-8").strip()   # convert bytes to a string and trim whitespace/newlines
            print("RX <-", packet[:80])         # log the incoming packet

            inner = packet[1:-1]                # remove the outer ( )
            ptype = inner.split(",", 1)[0].strip()  # first field is the packet type: CM, DP, End...

            if ptype == "End":                  # ---------- closing phase ----------
                send(conn, "(SC,Session closed)")   # acknowledge so the client knows it can disconnect
                break                           # exit the loop; the finally block closes everything

            elif ptype == "CM":                 # (CM,mode,arguments)
                if write_file:                  # a new command ends the previous openWrite
                    command_handler.close_file(write_file)  # flush and close the file that was being written
                    write_file = None           # mark that no file is open anymore

                parts = inner.split(",", 2)     # split into at most 3 parts so commas inside the arguments stay intact
                mode = parts[1].strip().lower() if len(parts) > 1 else ""   # command mode (prompt/openread/openwrite), "" if missing
                args = parts[2].strip() if len(parts) > 2 else ""           # the arguments, "" if missing

                if mode == "prompt":            # e.g. "mkdir docs", "ren a b"
                    command, _, rest = args.partition(" ")  # split at the first space: command name vs. its arguments
                    command = command.lower()   # make the command name case-insensitive
                    if command == "rd":         # "rd" is the short Windows alias for rmdir
                        command = "rmdir"       # map it to the real command name
                    send(conn, to_packet(command_handler.execute_prompt_command(command, rest.strip())))  # run the command, convert result to a packet, send it

                elif mode == "openread":        # send the file back in a Data Packet
                    result = command_handler.open_read(args)    # read the file whose path is in args
                    if result[0] == "SC":       # file was read successfully
                        send(conn, f"(DP,{encrypt(result[1], alg, key)})")  # send contents (encrypted if secured) inside a Data Packet
                    else:                       # file missing or unreadable
                        send(conn, to_packet(result))   # send the error packet instead

                elif mode == "openwrite":       # keep the file open for the Data Packets that follow
                    result = command_handler.open_write(args)   # open (or create) the file for writing
                    if result[0] == "SC":       # file opened fine
                        write_file = result[1]  # store the handle so later DP packets can write into it
                        send(conn, f"(SC,Ready to receive data for '{args}')")  # tell the client it may start sending data
                    else:                       # could not open the file
                        send(conn, to_packet(result))   # send the error packet

                else:                           # mode wasn't prompt, openread or openwrite
                    send(conn, f"(EE,E01,Unknown command type: {mode})")    # E01 = unknown command

            elif ptype == "DP":                 # (DP,text) - decrypt and write to the open file
                if write_file is None:          # client sent data without opening a file first
                    send(conn, "(EE,E04,No file open for writing - send openWrite first)")  # explain the correct order
                    continue                    # skip the rest and wait for the next packet
                text = inner.split(",", 1)[1] if "," in inner else ""   # everything after the first comma is the data payload
                try:
                    text = decrypt(text, alg, key)  # decrypt the payload (does nothing if unsecured)
                except Exception:               # wrong key, corrupted data, bad padding, etc.
                    send(conn, "(EE,E04,Decryption failed)")    # report the failure to the client
                    continue                    # wait for the next packet
                send(conn, to_packet(command_handler.write_data(write_file, text)))     # write the plain text to the file and reply with the result

            else:                               # packet type isn't End, CM or DP
                send(conn, f"(EE,E01,Unknown packet type: {ptype})")    # E01 = unknown command

    except OSError as e:                        # socket errors such as the client dropping suddenly
        print("Connection error:", e)           # log it instead of crashing the thread
    finally:                                    # runs no matter how we leave: normal end, error, or early return
        if write_file:                          # a file may still be open from an unfinished openWrite
            command_handler.close_file(write_file)  # close it so data is saved and the file isn't locked
        conn.close()                            # free this client's socket
        print("Disconnected:", addr)            # log that the client is gone


def start_server(host=HOST, port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create an IPv4 (AF_INET) TCP (SOCK_STREAM) socket
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # let us restart quickly without "address already in use" errors
    server.bind((host, port))                   # attach the socket to our IP address and port
    server.listen(10)                           # start listening; up to 10 waiting connections can queue
    print(f"RFMP server listening on {host}:{port}")    # tell the user the server is ready

    try:
        while True:                             # loop forever so we can accept any number of clients
            conn, addr = server.accept()        # block until a client connects; returns its socket and address
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()  # give the client its own thread; daemon=True lets the program exit even if threads are running
    except KeyboardInterrupt:                   # user pressed Ctrl+C
        print("\nServer stopped.")              # shutdown message
    finally:                                    # always runs when leaving the try block
        server.close()                          # release the listening port


if __name__ == "__main__":                      # True only when this file is run directly, not when imported
    start_server()                              # start the server with default host and port
