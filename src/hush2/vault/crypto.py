from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

IV_LENGTH = 12  # 96-bit nonce for GCM
KEY_LENGTH = 32  # 256-bit key
SALT_LENGTH = 16
PBKDF2_ITERATIONS = 100_000


def generate_salt() -> bytes:
    return os.urandom(SALT_LENGTH)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from a password using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode())


def encrypt(plaintext: str, key: bytes) -> tuple[bytes, bytes]:
    """Encrypt plaintext with AES-256-GCM. Returns (ciphertext, iv)."""
    iv = os.urandom(IV_LENGTH)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)
    return ciphertext, iv


def decrypt(ciphertext: bytes, iv: bytes, key: bytes) -> str:
    """Decrypt ciphertext with AES-256-GCM. Returns plaintext string."""
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext.decode()
