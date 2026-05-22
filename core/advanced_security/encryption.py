import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger("naps-chatbot-security")

class KMSStub:
    """
    A stub representing a Key Management Service (KMS) or HSM.
    In a real-world scenario, this would interact with AWS KMS, HashiCorp Vault, or Azure Key Vault.
    """
    def __init__(self):
        # Master key derived from environment variable, fallback to random if missing.
        master_secret = os.getenv("KMS_MASTER_SECRET", Fernet.generate_key().decode())
        self._master_key = master_secret.encode()

    def generate_data_key(self) -> bytes:
        """Generates a new data key for envelope encryption."""
        return Fernet.generate_key()

    def encrypt_data_key(self, data_key: bytes) -> bytes:
        """Encrypts the data key using the master key."""
        f = Fernet(self._master_key)
        return f.encrypt(data_key)

    def decrypt_data_key(self, encrypted_data_key: bytes) -> bytes:
        """Decrypts the data key using the master key."""
        f = Fernet(self._master_key)
        return f.decrypt(encrypted_data_key)

kms = KMSStub()

def encrypt_data(plaintext: str) -> dict:
    """
    Encrypts data using envelope encryption.
    Generates a unique data key, encrypts the data, and then encrypts the data key.
    """
    data_key = kms.generate_data_key()
    f = Fernet(data_key)
    ciphertext = f.encrypt(plaintext.encode())
    encrypted_data_key = kms.encrypt_data_key(data_key)
    
    return {
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode('utf-8'),
        "encrypted_data_key": base64.urlsafe_b64encode(encrypted_data_key).decode('utf-8')
    }

def decrypt_data(encrypted_payload: dict) -> str:
    """
    Decrypts data using envelope encryption.
    """
    try:
        encrypted_data_key = base64.urlsafe_b64decode(encrypted_payload["encrypted_data_key"])
        ciphertext = base64.urlsafe_b64decode(encrypted_payload["ciphertext"])
        
        data_key = kms.decrypt_data_key(encrypted_data_key)
        f = Fernet(data_key)
        return f.decrypt(ciphertext).decode('utf-8')
    except Exception as e:
        logger.error(f"[SEC_ERR] Decryption failed: {e}")
        raise ValueError("Decryption failed due to invalid key or corrupted data.")
