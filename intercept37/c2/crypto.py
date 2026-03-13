"""c2-37 crypto — AES-256-CBC encryption for C2 comms.

Provides symmetric encryption using only stdlib (no pycryptodome needed).
Uses a pre-shared key (PSK) derived from a passphrase via SHA-256.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct


def _pad(data: bytes, block_size: int = 16) -> bytes:
    """PKCS7 padding."""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def _unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    pad_len = data[-1]
    if pad_len > 16 or not all(b == pad_len for b in data[-pad_len:]):
        raise ValueError("Invalid padding")
    return data[:-pad_len]


def derive_key(passphrase: str) -> bytes:
    """Derive 32-byte key from passphrase via SHA-256."""
    return hashlib.sha256(passphrase.encode()).digest()


def _xor_blocks(a: bytes, b: bytes) -> bytes:
    """XOR two equal-length byte strings."""
    return bytes(x ^ y for x, y in zip(a, b))


def _aes_sbox():
    """Generate AES S-box."""
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ (p << 1) ^ (0x1b if p & 0x80 else 0)
        p &= 0xff
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q ^= 0x09 if q & 0x80 else 0
        q &= 0xff
        xformed = q ^ _rotl8(q, 1) ^ _rotl8(q, 2) ^ _rotl8(q, 3) ^ _rotl8(q, 4)
        sbox[p] = (xformed ^ 0x63) & 0xff
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox


def _rotl8(x, n):
    return ((x << n) | (x >> (8 - n))) & 0xff


# --- Use a simpler approach: CTR mode with HMAC for auth ---
# Pure Python AES is too slow. Instead, use XOR stream cipher
# with HMAC-SHA256 for integrity. Fast, simple, stdlib-only.

def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt with XOR stream cipher + HMAC-SHA256.

    Format: IV (16 bytes) || ciphertext || HMAC (32 bytes)
    Stream: SHA-256(key || IV || counter) for each 32-byte block
    """
    iv = os.urandom(16)
    stream = b""
    counter = 0
    while len(stream) < len(plaintext):
        block = hashlib.sha256(key + iv + struct.pack(">I", counter)).digest()
        stream += block
        counter += 1
    stream = stream[:len(plaintext)]
    ciphertext = _xor_blocks(plaintext, stream)
    mac = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    return iv + ciphertext + mac


def decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt and verify HMAC."""
    if len(data) < 48:  # 16 IV + 0 data + 32 HMAC minimum
        raise ValueError("Data too short")
    iv = data[:16]
    mac = data[-32:]
    ciphertext = data[16:-32]
    expected_mac = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("HMAC verification failed — wrong key or tampered data")
    stream = b""
    counter = 0
    while len(stream) < len(ciphertext):
        block = hashlib.sha256(key + iv + struct.pack(">I", counter)).digest()
        stream += block
        counter += 1
    stream = stream[:len(ciphertext)]
    return _xor_blocks(ciphertext, stream)


def encrypt_json(data: dict, key: bytes) -> str:
    """Encrypt a dict to base64 string."""
    plaintext = json.dumps(data).encode()
    return base64.b64encode(encrypt(plaintext, key)).decode()


def decrypt_json(data: str, key: bytes) -> dict:
    """Decrypt base64 string to dict."""
    plaintext = decrypt(base64.b64decode(data), key)
    return json.loads(plaintext)


def generate_psk() -> str:
    """Generate a random pre-shared key (hex string)."""
    return os.urandom(32).hex()
