import os
from cryptography.fernet import Fernet

def get_fernet():
    """
    Retrieves and initializes the Fernet symmetric encryption tool.

    Returns:
        Fernet | None: An initialized Fernet instance if the FERNET_KEY 
            environment variable is set, otherwise None.
    """
    key = os.getenv("FERNET_KEY")
    if not key:
        return None
    return Fernet(key.encode())

def encrypt(plaintext: str) -> str:
    """
    Encrypts a plaintext string using Fernet symmetric encryption.

    Args:
        plaintext (str): The raw string data to be encrypted.

    Returns:
        str: The encrypted ciphertext as a base64-encoded string.

    Raises:
        ValueError: If the process lacks the FERNET_KEY environment variable.
    """
    f = get_fernet()
    if not f:
        raise ValueError("FERNET_KEY not found in environment")
    return f.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """
    Decrypts a Fernet-encrypted ciphertext string back to plaintext.

    Args:
        ciphertext (str): The encrypted string data.

    Returns:
        str: The decrypted plaintext string.

    Raises:
        ValueError: If the process lacks the FERNET_KEY environment variable.
    """
    f = get_fernet()
    if not f:
        raise ValueError("FERNET_KEY not found in environment")
    return f.decrypt(ciphertext.encode()).decode()
