import socket
import sys

# ==============================================================================
# 1. PACKET BUILDERS
# =============================================================================

def build_start_packet(secured=False):
    """Generates Start-Packet: (SS,RFMP,v1.0,0) or (SS,RFMP,v1.0,1)"""
    sec_flag = "1" if secured else "0"
    return f"(SS,RFMP,v1.0,{sec_flag})"


def build_encryption_packet(algorithm, encrypted_session_key, username, client_pub_key):
    """Generates Encryption-Packet: (EC, Algorithm, session_key, username:Client_public_key)"""
    return f"(EC,{algorithm},{encrypted_session_key},{username}:{client_pub_key})"


def build_command_packet(cmd_mode, command_str):
    """Generates Command-Packet (prompt, openRead, openWrite)[cite: 1]."""
    return f"(CM,{cmd_mode},{command_str})"


def build_data_packet(text_payload):
    """Generates Data Packet for openWrite: (DP, text)[cite: 1]"""
    return f"(DP,{text_payload})"


def build_close_packet():
    """Generates Close-Packet: (End)[cite: 1]"""
    return "(End)"