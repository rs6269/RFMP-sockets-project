# CAESAR CIPHER
def caesar_encrypt(text: str, shift: int) -> str:  # defines the func, takes text & shift num, returns a string
    """Encrypts text using a Caesar cipher shift. Only shifts letters, leaves other chars untouched."""
    result = []  # empty list to hold our shifted letters
    for char in text:  
        if char.isalpha():  # check if its an actual letter so we dont mess up spaces or punctuation
            base = ord('A') if char.isupper() else ord('a')  # gets ascii starting point. 65 for uppercase, 97 for lowercase
            shifted = (ord(char) - base + shift) % 26  # core math: get ascii, subtract base, add shift, modulo 26 to wrap around
            result.append(chr(base + shifted))  # turn the new number back into a letter and add to list
        else:  # if it was a space or symbol
            result.append(char)  # just add it exactly as it is
    return ''.join(result)  # mash the list back into one single string and return it


def caesar_decrypt(text: str, shift: int) -> str:  # to decrypt, takes same inputs
    """Reverses a Caesar cipher shift - just encrypts with the negative shift."""
    return caesar_encrypt(text, -shift)  # just run the encrypt function backwards using a negative shift


# AES
from Crypto.Cipher import AES  # imports aes from pycryptodome library
from Crypto.Random import get_random_bytes  # need this to make random secure session keys
import base64  # needed to safely send messy binary bytes over a network socket


def generate_aes_key() -> bytes:  # to generate our session key
    """Generates a random 16-byte (128-bit) AES key."""
    return get_random_bytes(16)  # 16 bytes, random


def aes_encrypt(text: str, key: bytes) -> str:  # to encrypt data using our 16 byte key
    """Encrypts text with AES in EAX mode, Returns a base64 string containing
    #the nonce (number used once), tag, and ciphertext together so decrypt can pull them back apart"""
    cipher = AES.new(key, AES.MODE_EAX)  # create the aes lockbox. eax mode gives us a tamper-proof tag
    ciphertext, tag = cipher.encrypt_and_digest(text.encode('utf-8'))  # turn string to raw bytes, encrypt it, get the cipher and fingerprint tag
    combined = cipher.nonce + tag + ciphertext  # eax makes a random nonce. glue nonce, tag, and ciphertext together so server gets all 3
    return base64.b64encode(combined).decode('utf-8')  # convert raw bytes into a safe text string so the socket doesnt crash


def aes_decrypt(encrypted_text: str, key: bytes) -> str:  # reverse function for aes
    """Reverses aes_encrypt - pulls the nonce, tag, and ciphertext back apart and decrypts"""
    combined = base64.b64decode(encrypted_text)  # turn the safe base64 text back into messy raw bytes
    nonce = combined[:16]  # slice out the first 16 bytes, we know this is always the nonce
    tag = combined[16:32]  # slice out the next 16 bytes, this is always the tag
    ciphertext = combined[32:]  # everything left over is the actual encrypted message
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)  # rebuilds the lockbox using the key and the exact nonce we just extracted
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)  # decrypt and check the tag to make sure nobody messed with the packet
    return plaintext.decode('utf-8')  # turn raw bytes back to a readable python string


# RSA & PACKET FORMATTING
from Crypto.PublicKey import RSA  # import rsa module
from Crypto.Cipher import PKCS1_OAEP  # import the padding scheme for rsa


def generate_rsa_keypair():  # func to make public/private keys
    """Generates an RSA keypair. Returns (public_key_pem, private_key_pem) as strings,
    so they can be sent over the socket as plain text inside packets"""
    key = RSA.generate(2048)  # make a massive 2048 bit rsa object holding both keys
    private_key_pem = key.export_key().decode('utf-8')  # extract private key and format as a standard .pem (privacy enhanced mail) string
    public_key_pem = key.publickey().export_key().decode('utf-8')  # extract just the public part as a string too
    return public_key_pem, private_key_pem  # return both strings


def rsa_encrypt_session_key(session_key: bytes, public_key_pem: str) -> str:  # encrypt our aes key with servers public rsa key
    """Encrypts the AES session key using the recipient's RSA public key.
    Returns a base64 string so it can be embedded in a text packet."""
    public_key = RSA.import_key(public_key_pem)  # turn the servers string back into a usable rsa object
    cipher = PKCS1_OAEP.new(public_key)  # prep the rsa cipher using oaep padding for extra security
    encrypted = cipher.encrypt(session_key)  # lock our small 16-byte aes key inside the big rsa padlock
    return base64.b64encode(encrypted).decode('utf-8')  # convert to base64 safe text string for socket transport


def rsa_decrypt_session_key(encrypted_session_key: str, private_key_pem: str) -> bytes:  # func for server to decrypt
    """Decrypts the session key using our own RSA private key"""
    private_key = RSA.import_key(private_key_pem)  # turn private key string back to object
    cipher = PKCS1_OAEP.new(private_key)  # prep the cipher
    encrypted_bytes = base64.b64decode(encrypted_session_key)  # base64 text back to raw bytes
    decrypted = cipher.decrypt(encrypted_bytes)  # unlock it to get the raw 16-byte aes key back
    return decrypted  # return the usable aes key


def build_encryption_packet(algorithm: str, enc_session_key_b64: str, username: str, client_pub_key_pem: str) -> str:  # setup packet builder
    """Builds the RFMP Setup Phase Encryption Packet.
    Base64 encodes the client public key to strip newlines for safe socket transmission"""
    b64_client_pub = base64.b64encode(client_pub_key_pem.encode('utf-8')).decode('utf-8')  # rsa keys have hidden newlines. base64 flattens the WHOLE key into one safe line
    return f"(EC,{algorithm},{enc_session_key_b64},{username}:{b64_client_pub})"  # format exactly like the pdf asks for the setup phase


def parse_encryption_packet(packet_string: str) -> tuple:  # server parser
    """Parses the RFMP Setup Phase Encryption Packet back into its components.
    Strips the outer parentheses, splits fields, and base64-decodes the client public key"""
    clean_packet = packet_string.strip("()")  # delete the outer parenthesis off the packet

    # Split into a max of 4 parts to protect against stray commas in the username
    parts = clean_packet.split(",", 3)  # split by comma, max 3 times so we dont break if username has a comma in it

    if len(parts) != 4 or parts[0] != "EC":  # safety check for bad packets
        raise ValueError(f"Invalid Encryption Packet format: {packet_string[:50]}...")  # crash with helpful error

    algorithm = parts[1]  # save alg name
    enc_session_key_b64 = parts[2]  # save the encrypted aes key string

    # Split on the LAST colon: base64 never contains a colon, so this safely
    # isolates any colons that happen to be inside the username
    user_key_parts = parts[3].rsplit(":", 1)  # split the last chunk by colon starting from the right side just once
    if len(user_key_parts) != 2:  # another safety check
        raise ValueError("Invalid username:key format in packet")  # crash if split failed

    username = user_key_parts[0]  # first half is username
    b64_client_pub = user_key_parts[1]  # second half is the flattened public key

    client_pub_key_pem = base64.b64decode(b64_client_pub).decode('utf-8')  # un-flatten the base64 key back to multiline rsa string

    return algorithm, enc_session_key_b64, username, client_pub_key_pem  # spit out all 4 perfectly separated pieces


if __name__ == "__main__":
    # --- Caesar test ---
    original = "Hello RFMP"  # test string
    shift = 5  # test shift
    encrypted = caesar_encrypt(original, shift)  # run encrypt
    decrypted = caesar_decrypt(encrypted, shift)  # run decrypt
    print(f"Original:  {original}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    assert decrypted == original, "Caesar round trip failed!"  # crash if math is wrong
    print("Caesar Round trip OK")
    print()

    # --- AES test ---
    aes_key = generate_aes_key()  # make random key
    aes_encrypted = aes_encrypt(original, aes_key)  # encrypt test string
    aes_decrypted = aes_decrypt(aes_encrypted, aes_key)  # decrypt it
    print(f"AES Key (hex): {aes_key.hex()}")
    print(f"Encrypted:     {aes_encrypted}")
    print(f"Decrypted:     {aes_decrypted}")
    assert aes_decrypted == original, "AES round trip failed!"  # crash if it failed
    print("AES Round trip OK")
    print()

    # --- RSA test ---
    server_public, server_private = generate_rsa_keypair()  # make server keys
    client_public, client_private = generate_rsa_keypair()  # make client keys
    session_key = generate_aes_key()  # make the aes key to send

    encrypted_key = rsa_encrypt_session_key(session_key, server_public)  # client locks it
    decrypted_key = rsa_decrypt_session_key(encrypted_key, server_private)  # server unlocks it
    print(f"Original session key (hex):  {session_key.hex()}")
    print(f"Encrypted (base64, short):   {encrypted_key[:50]}...")
    print(f"Decrypted session key (hex): {decrypted_key.hex()}")
    assert decrypted_key == session_key, "RSA round trip failed!"  # verify handshake
    print("RSA Round trip OK")
    print()

    # --- Encryption-Packet build + parse test ---
    original_alg = "AES"  # fake alg choice
    original_user = "student_user,with:delimiters"  # stress test: comma AND colon in username

    packet = build_encryption_packet(original_alg, encrypted_key, original_user, client_public)  # build it
    print(f"Generated Encryption Packet (truncated):\n{packet[:100]}...")
    assert packet.startswith("(EC,AES,"), "Packet builder formatting failed!"  # check format
    print("Packet Builder OK")

    parsed_alg, parsed_enc_key, parsed_user, parsed_client_pub = parse_encryption_packet(packet)  # tear it apart
    assert parsed_alg == original_alg, "Algorithm parse failed!"  # check if we got alg back
    assert parsed_enc_key == encrypted_key, "Encrypted key parse failed!"  # check key
    assert parsed_user == original_user, "Username parse failed!"  # check username
    assert parsed_client_pub == client_public, "Client public key parse failed!"  # check pub key
    print("Packet Parse Round Trip OK")
    print()
    print("ALL TESTS PASSED")
