import os
from cryptography.fernet import Fernet

def get_fernet():
    key = os.getenv("FERNET_KEY")
    if not key:
        return None
    return Fernet(key.encode())

def encrypt(plaintext: str) -> str:
    f = get_fernet()
    if not f:
        raise ValueError("FERNET_KEY not found in environment")
    return f.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    f = get_fernet()
    if not f:
        raise ValueError("FERNET_KEY not found in environment")
    return f.decrypt(ciphertext.encode()).decode()
