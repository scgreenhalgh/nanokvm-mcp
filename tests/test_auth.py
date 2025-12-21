"""Tests for the auth module - CryptoJS-compatible AES password encryption."""

import base64
import hashlib
import urllib.parse

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from nanokvm_mcp.auth import encrypt_password, NANOKVM_PASSPHRASE, _evp_bytes_to_key


class TestEvpBytesToKey:
    """Tests for the _evp_bytes_to_key helper function (OpenSSL EVP_BytesToKey)."""

    @pytest.mark.unit
    def test_evp_bytes_to_key_produces_correct_length(self):
        """Should produce key and IV of correct lengths."""
        password = b"test"
        salt = b"12345678"

        key, iv = _evp_bytes_to_key(password, salt)

        assert len(key) == 32  # AES-256 key
        assert len(iv) == 16   # AES block size

    @pytest.mark.unit
    def test_evp_bytes_to_key_deterministic(self):
        """Same password and salt should produce same key/IV."""
        password = b"password"
        salt = b"saltsalt"

        key1, iv1 = _evp_bytes_to_key(password, salt)
        key2, iv2 = _evp_bytes_to_key(password, salt)

        assert key1 == key2
        assert iv1 == iv2

    @pytest.mark.unit
    def test_evp_bytes_to_key_different_salt(self):
        """Different salt should produce different key/IV."""
        password = b"password"

        key1, iv1 = _evp_bytes_to_key(password, b"salt1111")
        key2, iv2 = _evp_bytes_to_key(password, b"salt2222")

        assert key1 != key2
        assert iv1 != iv2

    @pytest.mark.unit
    def test_evp_bytes_to_key_custom_lengths(self):
        """Should work with custom key/IV lengths."""
        password = b"test"
        salt = b"12345678"

        key, iv = _evp_bytes_to_key(password, salt, key_len=16, iv_len=16)

        assert len(key) == 16
        assert len(iv) == 16


class TestEncryptPassword:
    """Tests for the encrypt_password function."""

    @pytest.mark.unit
    def test_encrypt_password_returns_url_encoded_base64(self):
        """Encrypted password should be URL-encoded base64."""
        encrypted = encrypt_password("test123")

        # URL decode first
        url_decoded = urllib.parse.unquote(encrypted)

        # Should be valid base64
        decoded = base64.b64decode(url_decoded)
        assert len(decoded) > 0

    @pytest.mark.unit
    def test_encrypt_password_starts_with_salted_prefix(self):
        """Encrypted data should start with 'Salted__' (OpenSSL format)."""
        encrypted = encrypt_password("test")
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)

        assert decoded[:8] == b"Salted__"

    @pytest.mark.unit
    def test_encrypt_password_contains_8_byte_salt(self):
        """After 'Salted__' prefix, there should be 8-byte salt."""
        encrypted = encrypt_password("test")
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)

        # Format: "Salted__" (8 bytes) + salt (8 bytes) + ciphertext
        assert len(decoded) >= 24  # 8 + 8 + at least 8 bytes ciphertext

    @pytest.mark.unit
    def test_encrypt_password_is_decryptable(self):
        """Encrypted password should be decryptable using CryptoJS-compatible method."""
        original = "mySecretPassword123"
        encrypted = encrypt_password(original)

        # URL decode
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)

        # Parse OpenSSL format
        assert decoded[:8] == b"Salted__"
        salt = decoded[8:16]
        ciphertext = decoded[16:]

        # Derive key/IV using EVP_BytesToKey
        key, iv = _evp_bytes_to_key(NANOKVM_PASSPHRASE.encode('utf-8'), salt)

        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

        assert decrypted.decode('utf-8') == original

    @pytest.mark.unit
    def test_encrypt_password_different_each_time(self):
        """Each encryption should produce different output due to random salt."""
        password = "samePassword"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # Same password should produce different ciphertext due to random salt
        assert encrypted1 != encrypted2

    @pytest.mark.unit
    def test_encrypt_password_empty_string(self):
        """Should handle empty password."""
        encrypted = encrypt_password("")
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)

        # Should still have Salted__ prefix + salt + encrypted block
        assert decoded[:8] == b"Salted__"
        assert len(decoded) >= 24

    @pytest.mark.unit
    def test_encrypt_password_unicode(self):
        """Should handle unicode passwords."""
        password = "密码テスト🔐"
        encrypted = encrypt_password(password)

        # Decrypt to verify
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)
        salt = decoded[8:16]
        ciphertext = decoded[16:]

        key, iv = _evp_bytes_to_key(NANOKVM_PASSPHRASE.encode('utf-8'), salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

        assert decrypted.decode('utf-8') == password

    @pytest.mark.unit
    def test_encrypt_password_long_password(self):
        """Should handle passwords longer than AES block size."""
        password = "a" * 1000
        encrypted = encrypt_password(password)

        # Decrypt to verify
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)
        salt = decoded[8:16]
        ciphertext = decoded[16:]

        key, iv = _evp_bytes_to_key(NANOKVM_PASSPHRASE.encode('utf-8'), salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

        assert decrypted.decode('utf-8') == password

    @pytest.mark.unit
    def test_nanokvm_passphrase_value(self):
        """Verify the hardcoded NanoKVM passphrase."""
        assert NANOKVM_PASSPHRASE == "nanokvm-sipeed-2024"

    @pytest.mark.unit
    def test_encrypt_password_special_characters(self):
        """Should handle passwords with special characters."""
        password = "p@$$w0rd!#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_password(password)

        # Decrypt to verify
        url_decoded = urllib.parse.unquote(encrypted)
        decoded = base64.b64decode(url_decoded)
        salt = decoded[8:16]
        ciphertext = decoded[16:]

        key, iv = _evp_bytes_to_key(NANOKVM_PASSPHRASE.encode('utf-8'), salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

        assert decrypted.decode('utf-8') == password
