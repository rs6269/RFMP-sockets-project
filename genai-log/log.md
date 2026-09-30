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