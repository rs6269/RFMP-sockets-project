## Caesar Cipher
Prompt: "give me a Caesar cipher encrypt/decrypt function in Python"
Output: [the code above]
Explanation: Each letter is converted to 0-25 based on its position in the 
alphabet, shifted by the key, then wrapped with %26 to stay in range. 
Non-letters are untouched. Decrypt just calls encrypt with a negative shift.


## AES Encryption
Prompt: "give me AES encrypt/decrypt functions in Python using pycryptodome"
Output: [see crypto.py — generate_aes_key, aes_encrypt, aes_decrypt]
Explanation: AES needs a random nonce (number used once) for every encryption 
so the same plaintext never produces the same ciphertext twice. MODE_EAX also 
produces a tag that proves the ciphertext wasn't tampered with during transit. 
Since decrypt needs the nonce, tag, and ciphertext together, all three are 
bundled into one base64 string by aes_encrypt so only one value has to be 
passed around instead of three. aes_decrypt just reverses that: splits the 
string back into its three parts and decrypts.

## RSA Keypair Generation & Session Key Encryption
Prompt: "give me RSA keypair generation and session key encrypt/decrypt functions in Python using pycryptodome"
Output: [see crypto.py — generate_rsa_keypair, rsa_encrypt_session_key, rsa_decrypt_session_key]
Explanation: RSA is asymmetric encryption — it uses a public key (safe to share, 
used to encrypt) and a private key (kept secret, used to decrypt). This means 
the session key can be sent securely without ever transmitting a shared secret 
over the network. PKCS1_OAEP is a padding scheme required for RSA to be secure; 
plain/raw RSA without padding is vulnerable to attacks. RSA itself is only 
used here to encrypt the small session key, not the actual file data, because 
RSA has a hard size limit on what it can encrypt — that's exactly why the 
protocol hands off to AES/Caesar (symmetric, no size limit) once the session 
key has been securely exchanged.