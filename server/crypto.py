# CAESAR CIPHER
def caesar_encrypt(text: str, shift: int) -> str:
    """Encrypts text using a Caesar cipher shift. Only shifts letters, leaves other chars untouched."""
    result = []
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            shifted = (ord(char) - base + shift) % 26
            result.append(chr(base + shifted))
        else:
            result.append(char)
    return ''.join(result)


def caesar_decrypt(text: str, shift: int) -> str:
    """Reverses a Caesar cipher shift — just encrypts with the negative shift."""
    return caesar_encrypt(text, -shift)



    # quick manual test
    original = "Hello RFMP"
    shift = 5
    encrypted = caesar_encrypt(original, shift)
    decrypted = caesar_decrypt(encrypted, shift)

    print(f"Original:  {original}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    assert decrypted == original, "Round trip failed!"
    print("Round trip OK ✅")


# AES
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

def generate_aes_key() -> bytes:
    """Generates a random 16-byte (128-bit) AES key."""
    return get_random_bytes(16)


def aes_encrypt(text: str, key: bytes) -> str:
    """Encrypts text with AES in EAX mode. Returns a base64 string containing
    the nonce, tag, and ciphertext together so decrypt can pull them back apart."""
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(text.encode('utf-8'))
    # bundle nonce + tag + ciphertext so we only need to pass one string around
    combined = cipher.nonce + tag + ciphertext
    return base64.b64encode(combined).decode('utf-8')


def aes_decrypt(encrypted_text: str, key: bytes) -> str:
    """Reverses aes_encrypt — pulls the nonce, tag, and ciphertext back apart and decrypts."""
    combined = base64.b64decode(encrypted_text)
    nonce = combined[:16]
    tag = combined[16:32]
    ciphertext = combined[32:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode('utf-8')



    # quick manual test
    key = generate_aes_key()
    original = "Hello RFMP"
    encrypted = aes_encrypt(original, key)
    decrypted = aes_decrypt(encrypted, key)

    print(f"Key (hex):  {key.hex()}")
    print(f"Original:   {original}")
    print(f"Encrypted:  {encrypted}")
    print(f"Decrypted:  {decrypted}")
    assert decrypted == original, "Round trip failed!"
    print("Round trip OK ✅")


# RSA & PACKET FORMATTING
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

def generate_rsa_keypair():
    """Generates an RSA keypair. Returns (public_key_pem, private_key_pem) as strings,
    so they can be sent over the socket as plain text inside packets."""
    key = RSA.generate(2048)
    private_key_pem = key.export_key().decode('utf-8')
    public_key_pem = key.publickey().export_key().decode('utf-8')
    return public_key_pem, private_key_pem


def rsa_encrypt_session_key(session_key: bytes, public_key_pem: str) -> str:
    """Encrypts the AES session key using the recipient's RSA public key.
    Returns a base64 string so it can be embedded in a text packet."""
    public_key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(public_key)
    encrypted = cipher.encrypt(session_key)
    return base64.b64encode(encrypted).decode('utf-8')


def rsa_decrypt_session_key(encrypted_session_key: str, private_key_pem: str) -> bytes:
    """Decrypts the session key using our own RSA private key."""
    private_key = RSA.import_key(private_key_pem)
    cipher = PKCS1_OAEP.new(private_key)
    encrypted_bytes = base64.b64decode(encrypted_session_key)
    decrypted = cipher.decrypt(encrypted_bytes)
    return decrypted


def build_encryption_packet(algorithm: str, enc_session_key_b64: str, username: str, client_pub_key_pem: str) -> str:
    """Builds the RFMP Setup Phase Encryption Packet.
    Base64 encodes the client public key to strip newlines for safe socket transmission."""
    b64_client_pub = base64.b64encode(client_pub_key_pem.encode('utf-8')).decode('utf-8')
    return f"(EC,{algorithm},{enc_session_key_b64},{username}:{b64_client_pub})"

def parse_encryption_packet(packet_string: str) -> tuple:
    """Parses the RFMP Setup Phase Encryption Packet back into its components.
    Strips the outer parentheses, splits fields, and base64-decodes the client public key."""
    clean_packet = packet_string.strip("()")
    
    # Split into a max of 4 parts to protect against stray commas in the username
    parts = clean_packet.split(",", 3)
    
    if len(parts) != 4 or parts[0] != "EC":
        raise ValueError(f"Invalid Encryption Packet format: {packet_string[:50]}...")
        
    algorithm = parts[1]
    enc_session_key_b64 = parts[2]
    
    # FIX: Use rsplit(":", 1) to split on the LAST colon. 
    # Base64 strings don't contain colons, so this safely isolates any colons inside the username.
    user_key_parts = parts[3].rsplit(":", 1)
    if len(user_key_parts) != 2:
         raise ValueError("Invalid username:key format in packet")
         
    username = user_key_parts[0]
    b64_client_pub = user_key_parts[1]
    
    client_pub_key_pem = base64.b64decode(b64_client_pub).decode('utf-8')
    
    return algorithm, enc_session_key_b64, username, client_pub_key_pem


    # --- RSA & Packet Builder/Parser Tests (Replaces all previous RSA test blocks) ---
    server_public, server_private = generate_rsa_keypair()
    client_public, client_private = generate_rsa_keypair()
    
    session_key = generate_aes_key()

    # Test RSA Handshake
    encrypted_key = rsa_encrypt_session_key(session_key, server_public)
    decrypted_key = rsa_decrypt_session_key(encrypted_key, server_private)
    assert decrypted_key == session_key, "Round trip failed!"
    print("RSA Round trip OK ✅")
    
    # Test Packet Construction & Parsing
    original_alg = "AES"
    original_user = "student_user,with:delimiters" 
    
    # 1. Build
    packet = build_encryption_packet(original_alg, encrypted_key, original_user, client_public)
    print(f"\nGenerated Encryption Packet (truncated):\n{packet[:100]}...")
    assert packet.startswith("(EC,AES,"), "Packet builder formatting failed!"
    print("Packet Builder OK ✅")

    # 2. Parse
    parsed_alg, parsed_enc_key, parsed_user, parsed_client_pub = parse_encryption_packet(packet)
    
    # 3. Verify (This will now pass even with colons in the username)
    assert parsed_alg == original_alg, "Algorithm parse failed!"
    assert parsed_enc_key == encrypted_key, "Encrypted key parse failed!"
    assert parsed_user == original_user, "Username parse failed!"
    assert parsed_client_pub == client_public, "Client public key parse failed!"
    
    print("Packet Parse Round Trip OK ✅")


if __name__ == "__main__":
    # quick manual test, simulating the server generating a keypair, the client

    server_public, server_private = generate_rsa_keypair()
    client_public, client_private = generate_rsa_keypair()
    
    session_key = generate_aes_key()

    encrypted_key = rsa_encrypt_session_key(session_key, server_public)
    decrypted_key = rsa_decrypt_session_key(encrypted_key, server_private)

    print(f"Original session key (hex):    {session_key.hex()}")
    print(f"Encrypted (base64, truncated): {encrypted_key[:50]}...")
    print(f"Decrypted session key (hex):   {decrypted_key.hex()}")
    assert decrypted_key == session_key, "Round trip failed!"
    print("RSA Round trip OK ✅")
    
    # test packet builder
    packet = build_encryption_packet("AES", encrypted_key, "student", client_public)
    print(f"\nGenerated Encryption Packet (truncated):\n{packet[:100]}...")
    assert packet.startswith("(EC,AES,"), "Packet builder formatting failed!"
    print("Packet Builder OK ✅")