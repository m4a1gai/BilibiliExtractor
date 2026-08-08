"""weapi request encryption used by the NetEase Cloud Music web client.

This mirrors the widely published scheme used by open-source NetEase
clients: the JSON payload is AES-encrypted twice (first with a fixed
nonce, then with a random per-request key), and the random key is
itself RSA-"encrypted" with NetEase's public modulus so the server can
recover it.
"""
from __future__ import annotations

import base64
import binascii
import json
import random
import string

from Crypto.Cipher import AES

_NONCE = b"0CoJUm6Qyw8W8jud"
_IV = b"0102030405060708"
_PUBKEY_EXP = 0x010001
_MODULUS = int(
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876a"
    "ea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c"
    "4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289d"
    "c6935b3ece0462db0a22b8e7",
    16,
)


def _random_key(length: int = 16) -> bytes:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length)).encode()


def _aes_encrypt(text: bytes, key: bytes) -> bytes:
    pad = 16 - len(text) % 16
    text += bytes([pad]) * pad
    cipher = AES.new(key, AES.MODE_CBC, _IV)
    return base64.b64encode(cipher.encrypt(text))


def _rsa_encrypt(text: bytes, pubkey_exp: int, modulus: int) -> str:
    reversed_hex = binascii.hexlify(text[::-1])
    value = pow(int(reversed_hex, 16), pubkey_exp, modulus)
    return format(value, "x").zfill(256)


def weapi(data: dict) -> dict:
    """Encrypts a payload dict into the {params, encSecKey} form the
    NetEase weapi endpoints expect as application/x-www-form-urlencoded body."""
    text = json.dumps(data).encode()
    secret_key = _random_key()
    params = _aes_encrypt(_aes_encrypt(text, _NONCE), secret_key)
    enc_sec_key = _rsa_encrypt(secret_key, _PUBKEY_EXP, _MODULUS)
    return {"params": params.decode(), "encSecKey": enc_sec_key}
