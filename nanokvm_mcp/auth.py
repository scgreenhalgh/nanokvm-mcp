"""Authentication utilities for NanoKVM API."""

import base64
import hashlib
import os
import urllib.parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# NanoKVM uses this passphrase for password encryption
NANOKVM_PASSPHRASE = "nanokvm-sipeed-2024"


def _evp_bytes_to_key(
    password: bytes,
    salt: bytes,
    key_len: int = 32,
    iv_len: int = 16,
) -> tuple[bytes, bytes]:
    """
    Derive key and IV using OpenSSL's EVP_BytesToKey (MD5-based).

    This matches CryptoJS's default key derivation when using a passphrase.
    """
    d = b""
    d_i = b""

    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i

    return d[:key_len], d[key_len:key_len + iv_len]


def encrypt_password(password: str) -> str:
    """
    Encrypt password using CryptoJS-compatible AES encryption.

    The NanoKVM frontend uses CryptoJS.AES.encrypt with a passphrase,
    which uses OpenSSL's EVP_BytesToKey for key derivation and produces
    output in the format: "Salted__" + salt + ciphertext (base64 encoded).

    Args:
        password: Plain text password

    Returns:
        Base64 encoded string matching CryptoJS output format
    """
    # Generate random 8-byte salt (same as CryptoJS)
    salt = os.urandom(8)

    # Derive key and IV using EVP_BytesToKey (MD5-based, like CryptoJS)
    key, iv = _evp_bytes_to_key(NANOKVM_PASSPHRASE.encode('utf-8'), salt)

    # Encrypt with AES-256-CBC
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(password.encode('utf-8'), AES.block_size)
    ciphertext = cipher.encrypt(padded_data)

    # Format: "Salted__" + salt + ciphertext (OpenSSL format)
    openssl_data = b"Salted__" + salt + ciphertext

    # Base64 encode, then URL encode (as the frontend does)
    b64_encoded = base64.b64encode(openssl_data).decode('utf-8')
    return urllib.parse.quote(b64_encoded, safe='')
