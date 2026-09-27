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


if __name__ == "__main__":
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