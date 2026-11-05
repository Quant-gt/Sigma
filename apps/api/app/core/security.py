# apps/api/app/core/security.py
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class BrokerCredentialVault:
    """
    AES-256-GCM authenticated encryption for Broker OAuth Access Tokens & Secrets.
    Master key is loaded strictly from environment/KMS, never stored in Postgres.
    """
    def __init__(self, master_key_hex: str | None = None):
        raw_hex = master_key_hex or os.environ.get("QUANTRA_MASTER_KMS_KEY_HEX")
        if not raw_hex or len(bytes.fromhex(raw_hex)) != 32:
            raise RuntimeError("QUANTRA_MASTER_KMS_KEY_HEX must be a 32-byte (64 hex char) AES-256 key.")
        self._aesgcm = AESGCM(bytes.fromhex(raw_hex))

    def encrypt_secret(self, plaintext: str, associated_user_id: str) -> bytes:
        nonce = os.urandom(12)  # 96-bit NIST recommended GCM nonce
        aad = associated_user_id.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
        return base64.b64encode(nonce + ciphertext)

    def decrypt_secret(self, encrypted_blob: bytes, associated_user_id: str) -> str:
        raw = base64.b64decode(encrypted_blob)
        nonce, ciphertext = raw[:12], raw[12:]
        aad = associated_user_id.encode("utf-8")
        plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext_bytes.decode("utf-8")
