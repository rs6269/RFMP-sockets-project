import socket
import sys

# ==============================================================================
# 1. PACKET BUILDERS
# =============================================================================

def parse_packet(packet_str):
    
    #Parses incoming raw packet strings received from the server into structured dictionaries.

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
        # Confirm Connection packet: (CC) or (CC, Server_public_key)[cite: 1]
        pub_key = parts[1] if len(parts) > 1 else None
        return {"type": "CC", "server_pub_key": pub_key}
        
    elif p_type == "SC":
        # Success confirmation packet: (SC, message)[cite: 1]
        data = ",".join(parts[1:]) if len(parts) > 1 else "Operation successful."
        return {"type": "SC", "data": data}
        
    elif p_type == "EE":
        # Exception Event (Error) packet: (EE, Error Code, Description)[cite: 1]
        err_code = parts[1] if len(parts) > 1 else "ERR_UNKNOWN"
        err_desc = ",".join(parts[2:]) if len(parts) > 2 else "Unspecified error."
        return {"type": "EE", "code": err_code, "description": err_desc}
        
    elif p_type == "DP":
        # Data packet: (DP, payload_text)[cite: 1]
        text = ",".join(parts[1:]) if len(parts) > 1 else ""
        return {"type": "DP", "text": text}
    
    return {"type": p_type, "raw_parts": parts}


def build_start_packet(secured=False):

    #Constructs the protocol Start-Packet.
    sec_flag = "1" if secured else "0"
    return f"(SS,RFMP,v1.0,{sec_flag})"


def build_encryption_packet(algorithm, encrypted_session_key, username, client_pub_key):
    
    #Constructs the Encryption-Packet for secure communication sessions.
    return f"(EC,{algorithm},{encrypted_session_key},{username}:{client_pub_key})"


def build_command_packet(cmd_mode, command_str):
    
    #Constructs Command-Packets for folder operations, system queries, or file streams.
    return f"(CM,{cmd_mode},{command_str})"


def build_data_packet(text_payload):
    
    #Constructs Data Packets used during file writing operations (openWrite).
    return f"(DP,{text_payload})"


def build_close_packet():
    
    #Constructs the Session Termination Close-Packet.
    return "(End)"


# ===============================================================
# 2. EE (ERROR) DETECTION
# ===============================================================

def handle_server_response(response_str):
    
    #Dispatches and handles incoming server responses. 
    #Crucially identifies and displays Exception Event (EE) error packets[cite: 1].
    
    parsed = parse_packet(response_str)
    
    # Checking if the server returned an Exception Event (EE) packet[cite: 1]
    if parsed["type"] == "EE":
        print("\n" + "!" * 60)
        print(f"[!] EXCEPTION EVENT DETECTED (EE PACKET)")
        print(f"    Error Code:  {parsed['code']}")
        print(f"    Description: {parsed['description']}")
        print("!" * 60 + "\n")
        return False, parsed
    
    elif parsed["type"] == "SC":
        print(f"\n[+] [SUCCESS]: {parsed['data']}\n")
        return True, parsed
    
    elif parsed["type"] == "CC":
        print(f"\n[+] Connection Confirmed (CC). Server PubKey: {parsed['server_pub_key']}\n")
        return True, parsed
    
    elif parsed["type"] == "DP":
        print(f"\n[+] Data Packet Received:\n{parsed['text']}\n")
        return True, parsed
    
    return True, parsed