import socket
import sys
import os
import secrets  # used to pick a random Caesar shift key

# Add relative path to 'server' folder so crypto.py can be found from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

# Import cryptographic functions from crypto file
try:
    from Raihan_crypto import (
        generate_rsa_keypair,
        rsa_encrypt_session_key,
        generate_aes_key,
        aes_encrypt,
        aes_decrypt,
        caesar_encrypt,
        caesar_decrypt,
        build_encryption_packet as build_ec_packet
    )
except ImportError:
    print("[-] Warning: crypto.py not found in working directory. Crypto functions disabled.")

# ============================================
# 1. PACKET BUILDERS
# ============================================

def parse_packet(packet_str):
    
    #Parses incoming raw packet strings received from the server into structured dictionaries

    # Clean up surrounding whitespace
    cleaned = packet_str.strip()
    
    # Strip opening and closing parentheses defining the packet envelope
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    
    # Split fields by commas and strip whitespace from each part
    parts = [p.strip() for p in cleaned.split(",")]
    if not parts or not parts[0]:
        return {"type": "UNKNOWN", "raw": packet_str}
    
    p_type = parts[0]
    
    # Parse based on explicit RFMP packet types
    if p_type == "CC":
        # Confirm Connection packet: (CC) or (CC, Server_public_key)
        pub_key = parts[1] if len(parts) > 1 else None
        return {"type": "CC", "server_pub_key": pub_key}
        
    elif p_type == "SC":
        # Success confirmation packet: (SC, message)
        data = ",".join(parts[1:]) if len(parts) > 1 else "Operation successful."
        return {"type": "SC", "data": data}
        
    elif p_type == "EE":
        # Exception Event (Error) packet: (EE, Error Code, Description)
        err_code = parts[1] if len(parts) > 1 else "ERR_UNKNOWN"
        err_desc = ",".join(parts[2:]) if len(parts) > 2 else "Unspecified error."
        return {"type": "EE", "code": err_code, "description": err_desc}
        
    elif p_type == "DP":
        # Data packet: (DP, payload_text)
        # split only once so commas and spaces inside the data stay exactly as sent
        text = cleaned.split(",", 1)[1] if "," in cleaned else ""
        return {"type": "DP", "text": text}
    
    return {"type": p_type, "raw_parts": parts}


def build_start_packet(secured=False):

    #Constructs the protocol Start-Packet
    sec_flag = "1" if secured else "0"
    return f"(SS,RFMP,v1.0,{sec_flag})"


def build_command_packet(cmd_mode, command_str):
    
    #Constructs Command-Packets for folder operations, system queries, or file streams
    return f"(CM,{cmd_mode},{command_str})"


def build_data_packet(text_payload):
    
    #Constructs Data Packets used during file writing operations (openWrite)
    return f"(DP,{text_payload})"


def build_close_packet():
    
    #Constructs the Session Termination Close-Packet
    return "(End)"


# ===================================
# 2. EE (ERROR) DETECTION
# ===================================

def handle_server_response(response_str):
    
    #Dispatches and handles incoming server responses
    #Crucially identifies and displays Exception Event (EE) error packets
    
    parsed = parse_packet(response_str)
    
    # Checking if the parsed packet type indicates an Exception Event (EE)
    if parsed["type"] == "EE":
        # Print a highly visible formatted alert frame for debugging and UI feedback
        print("\n" + "!" * 60)
        print(f"[!] EXCEPTION EVENT DETECTED (EE PACKET)")
        print(f"    Error Code:  {parsed['code']}")
        print(f"    Description: {parsed['description']}")
        print("!" * 60 + "\n")
        # Return False to signify that the operation encountered a server-side exception
        return False, parsed
    
    # Handle standard success confirmation packets (SC)
    elif parsed["type"] == "SC":
        print(f"\n[+] [SUCCESS]: {parsed['data']}\n")
        return True, parsed
    
    # Handle connection confirmation handshake packets (CC)
    elif parsed["type"] == "CC":
        print(f"\n[+] Connection Confirmed (CC). Server PubKey: {parsed['server_pub_key']}\n")
        return True, parsed
    
    # Handle incoming file text payloads or data streams (DP)
    elif parsed["type"] == "DP":
        print(f"\n[+] Data Packet Received:\n{parsed['text']}\n")
        return True, parsed
    
    # Default fallback for unmapped or custom response structures
    return True, parsed


# ===========================================================================
# SECTION 3: REAL SOCKET NETWORK LAYER (CONNECTS TO server.py)
# ===========================================================================

class ServerSocketConnection:
    
    # Manages TCP socket connectivity with the groups central server module (server.py)
    
    # Detailed Logic:
    #    - Establishes standard AF_INET/SOCK_STREAM network sockets
    #    - Handles connecting to localhost on the designated port (5000)
    #    - Encodes outgoing text commands into UTF-8 bytes for transmission
    #    - Manages buffer read limits and safe socket closure routines
    
    def __init__(self, host="127.0.0.1", port=5000):
        # Initializes the socket instance and connects to the active server listener

        # Instantiate a standard IPv4 TCP socket object
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[*] Attempting connection to server at {host}:{port}...")
        
        # Connect the socket to the server address tuple (IP, Port)
        self.sock.connect((host, port))
        print("[+] Socket connection established successfully!")

    def send_and_receive(self, packet_str):
        
        #Transmits a formatted protocol string over the active socket and blocks for the reply.
        
        print(f"\n[TX -> Server]: {packet_str}")
        
        # Convert string packet into UTF-8 encoded bytes and send completely over TCP
        self.sock.sendall(packet_str.encode('utf-8'))
        
        # Block and listen for incoming socket data (buffer size: 1MB)
        data = self.sock.recv(1024 * 1024)
        
        # Handle edge case where server abruptly terminates or drops connection
        if not data:
            return "(EE, ERR_00, Connection terminated by remote host)"
            
        # Decode incoming raw byte stream back into a readable string
        response_str = data.decode('utf-8')
        print(f"[RX <- Server]: {response_str}")
        return response_str

    def close(self):
        # Closes the active socket connection
        try:
            self.sock.close()
        except Exception:
            pass

def encrypt_payload(text, algorithm, key):
    #Encrypts file text with whichever algorithm was chosen for this session
    if algorithm == "AES":
        return aes_encrypt(text, key)
    if algorithm == "CAESAR":
        return caesar_encrypt(text, key)
    return text


def decrypt_payload(text, algorithm, key):
    #Decrypts file text with whichever algorithm was chosen for this session
    if algorithm == "AES":
        return aes_decrypt(text, key)
    if algorithm == "CAESAR":
        return caesar_decrypt(text, key)
    return text


# ========================================================
# SECTION 4: CLIENT INTERACTIVE MENU & UI LOGIC
# ========================================================
def run_client_app():

    #Main interactive loop that gives a user-friendly UI
    
    #Detailed Logic:
    #    1. Attempts binding a live socket connection to the server.py listener
    #    2. Prompts user for security preference and transmits the protocol Start-Packet (SS)
    #    3. Enters an infinite menu loop allowing selection of file operations, system commands, or error triggers
    #    4. Automatically constructs packets based on inputs, transmits via socket, and routes responses
    #    5. Handles clean session teardown via the End close packet upon user exit
   
    print("==================================================")
    print("   RFMP Client Application (Live Socket Mode)     ")
    print("==================================================")
    
    # Try initializing the network socket connection; catch exceptions if server is offline
    try:
        conn = ServerSocketConnection(host="127.0.0.1", port=5000)
    except ConnectionRefusedError:
        print("[-] Error: Connection refused on port 5000. Ensure server.py is running first!")
        return

    # Handshake initialization phase: Check security requirements
    sec_choice = input("Enable Secure Communication? (0=No, 1=Yes) [0/1]: ").strip()
    is_secure = (sec_choice == "1")
    algorithm = None   # "AES" or "CAESAR" (only set when the session is secured)
    session_key = None # Holds the active session key (16 bytes for AES, a number for Caesar)
    
    # Build and send the mandatory start-packet (SS) to initiate protocol dialogue
    start_pkt = build_start_packet(secured=is_secure)
    resp = conn.send_and_receive(start_pkt)
    success, parsed_start = handle_server_response(resp)
    
    # Terminate sequence if server rejects the start handshake
    if not success:
        print("[-] Handshake protocol rejected. Closing connection.")
        conn.close()
        return

    # Perform RSA Key Exchange and send (EC) Packet if Secured
    if is_secure:
        server_pub_key_pem = parsed_start.get("server_pub_key")
        
        # 1. Let the user choose the algorithm, then generate the session key for it
        alg_choice = input("Choose algorithm (1=AES, 2=Caesar) [1/2]: ").strip()
        if alg_choice == "2":
            algorithm = "CAESAR"
            session_key = secrets.randbelow(25) + 1          # random Caesar shift from 1 to 25
            key_bytes = str(session_key).encode("utf-8")     # the shift is sent as text, the server converts it back to a number
        else:
            algorithm = "AES"
            session_key = generate_aes_key()                 # random 16-byte AES key
            key_bytes = session_key
        
        # 2. Encrypt the session key with server's RSA public key
        encrypted_session_key_b64 = rsa_encrypt_session_key(key_bytes, server_pub_key_pem)
        
        # 3. Generate client RSA keypair
        client_pub_key_pem, client_priv_key_pem = generate_rsa_keypair()
        username = "raihan_user"
        
        # 4. Build and send Encryption Packet (EC) via crypto.py
        ec_pkt = build_ec_packet(algorithm, encrypted_session_key_b64, username, client_pub_key_pem)
        ec_resp = conn.send_and_receive(ec_pkt)
        ec_success, _ = handle_server_response(ec_resp)
        
        if not ec_success:
            print("[-] Encryption setup handshake failed. Terminating session.")
            conn.close()
            return
            
        print(f"[+] Secure {algorithm} Key Exchange Completed Successfully!")

    # Continuous interactive menu loop for executing remote commands
    while True:
        print("--------------------------------------------------")
        print("RFMP Client Main Menu:")
        print("  1. Folder Commands (mkdir, cd, rmdir, del, ren)")
        print("  2. System Commands (dir, pwd, move, type, copy)")
        print("  3. openRead  (Retrieve remote file contents)")
        print("  4. openWrite (Write text payload to remote file)")
        print("  5. Test EE Exception Packet (Trigger server error response)")
        print("  6. Exit (Send End Packet & Close Session)")
        print("--------------------------------------------------")
        
        choice = input("Select an option (1-6): ").strip()
        
        # Option 1: Execute directory or folder manipulation commands
        if choice == "1":
            cmd = input("Enter folder command (mkdir / cd / rmdir / del / ren): ").strip()
            args = input("Enter arguments (e.g., folderName or oldName newName): ").strip()
            pkt = build_command_packet("prompt", f"{cmd} {args}")
            resp = conn.send_and_receive(pkt)
            handle_server_response(resp)

        # Option 2: Execute general OS system prompt commands
        elif choice == "2":
            sys_cmd = input("Enter system command (e.g.,dir, pwd, move, type, copy): ").strip()
            pkt = build_command_packet("prompt", sys_cmd)
            resp = conn.send_and_receive(pkt)
            handle_server_response(resp)

        # Option 3: Request remote file read streams via openRead mode
        elif choice == "3":
            filename = input("Enter remote filename to read: ").strip()
            pkt = build_command_packet("openRead", filename)
            resp = conn.send_and_receive(pkt)
            success, parsed_dp = handle_server_response(resp)
            
            # Decrypt received file payload (AES or Caesar) if in secure mode
            if success and is_secure and session_key is not None and parsed_dp.get("type") == "DP":
                raw_cipher = parsed_dp.get("text", "")
                try:
                    decrypted_text = decrypt_payload(raw_cipher, algorithm, session_key)
                    print(f"[+] Decrypted File Payload:\n{decrypted_text}\n")
                except Exception as e:
                    print(f"[-] {algorithm} Decryption Error: {e}")

        # Option 4: Write text data streams to remote files via openWrite mode
        elif choice == "4":
            filename = input("Enter remote filename to write: ").strip()
            pkt = build_command_packet("openWrite", filename)
            resp = conn.send_and_receive(pkt)
            handle_server_response(resp)
            
            payload = input("Enter text data payload to save: ")
            
            # Encrypt file payload (AES or Caesar) if operating in secure mode
            if is_secure and session_key is not None:
                payload = encrypt_payload(payload, algorithm, session_key)
            dp_pkt = build_data_packet(payload)
            resp_dp = conn.send_and_receive(dp_pkt)
            handle_server_response(resp_dp)
        
        # Option 5: Explicit test utility triggering server-side exception handling (EE packet display)
        elif choice == "5":
            pkt = build_command_packet("prompt", "cd /nonexistent_folder_fail")
            resp = conn.send_and_receive(pkt)
            handle_server_response(resp)

        # Option 6: Termination sequence
        elif choice == "6":
            # Transmit the End close packet to signal shutdown to the server
            close_pkt = build_close_packet()
            conn.send_and_receive(close_pkt)
            print("Session successfully closed.")
            conn.close()
            break
        else:
            print("Invalid option selected. Please choose between 1 and 6.")

# =========================================
# SECTION 4: STANDALONE UNIT TESTS
# =========================================

def test_client_functions_alone():
    #Performs standalone unit tests using custom conditional validation checks and detailed status printouts

    print("[*] Executing 'Test Alone' suite on client functions...\n")
    
    tests_passed = 0
    total_tests = 7

    # Test 1: Start Packet (Unsecured)
    res1 = build_start_packet(False)
    exp1 = "(SS,RFMP,v1.0,0)"
    if res1 == exp1:
        print(f"  [PASS] Test 1 (Start Unsecured): {res1}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 1: Expected {exp1}, got {res1}")

    # Test 2: Start Packet (Secured)
    res2 = build_start_packet(True)
    exp2 = "(SS,RFMP,v1.0,1)"
    if res2 == exp2:
        print(f"  [PASS] Test 2 (Start Secured):   {res2}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 2: Expected {exp2}, got {res2}")

    # Test 3: Encryption Packet
    res3 = build_ec_packet("AES", "key123", "alice", "pub456")
    exp3 = "(EC,AES,key123,alice:cHViNDU2)"
    if res3 == exp3:
        print(f"  [PASS] Test 3 (Encryption):      {res3}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 3: Expected {exp3}, got {res3}")

    # Test 4: Command Packet
    res4 = build_command_packet("prompt", "mkdir test")
    exp4 = "(CM,prompt,mkdir test)"
    if res4 == exp4:
        print(f"  [PASS] Test 4 (Command):         {res4}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 4: Expected {exp4}, got {res4}")

    # Test 5: Data Packet
    res5 = build_data_packet("hello")
    exp5 = "(DP,hello)"
    if res5 == exp5:
        print(f"  [PASS] Test 5 (Data Packet):     {res5}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 5: Expected {exp5}, got {res5}")

    # Test 6: Close Packet
    res6 = build_close_packet()
    exp6 = "(End)"
    if res6 == exp6:
        print(f"  [PASS] Test 6 (Close Packet):    {res6}")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 6: Expected {exp6}, got {res6}")

    # Test 7: Exception Event (EE) Packet Parser
    parsed_ee = parse_packet("(EE, ERR_02, Requested file not found)")
    if parsed_ee["type"] == "EE" and parsed_ee["code"] == "ERR_02":
        print(f"  [PASS] Test 7 (EE Parser):       Successfully parsed error code ERR_02")
        tests_passed += 1
    else:
        print(f"  [FAIL] Test 7 (EE Parser):       Failed to parse EE packet correctly")

    print(f"\n[+] Test Summary: {tests_passed}/{total_tests} standalone tests completed successfully!\n")

# ====================================
# SCRIPT ENTRY POINT
# ====================================

if __name__ == "__main__":
    # 1. Execute standalone function test assertions first to confirm internal code health[cite: 1]
    test_client_functions_alone()
    
    # 2. Launch the interactive client application console user interface menu loop[cite: 1, 3]
    run_client_app()
