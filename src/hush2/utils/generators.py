from __future__ import annotations

import base64
import secrets
import string
import uuid


def generate_password(
    length: int = 32,
    uppercase: bool = True,
    lowercase: bool = True,
    digits: bool = True,
    symbols: bool = True,
) -> str:
    charset = ""
    required: list[str] = []
    if uppercase:
        charset += string.ascii_uppercase
        required.append(secrets.choice(string.ascii_uppercase))
    if lowercase:
        charset += string.ascii_lowercase
        required.append(secrets.choice(string.ascii_lowercase))
    if digits:
        charset += string.digits
        required.append(secrets.choice(string.digits))
    if symbols:
        charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        required.append(secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"))

    if not charset:
        charset = string.ascii_letters + string.digits

    remaining = length - len(required)
    if remaining < 0:
        remaining = 0
    chars = required + [secrets.choice(charset) for _ in range(remaining)]

    result = list(chars)
    for i in range(len(result) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        result[i], result[j] = result[j], result[i]

    return "".join(result[:length])


def generate_token(nbytes: int = 32, encoding: str = "hex") -> str:
    """Generate a random token (hex or base64)."""
    raw = secrets.token_bytes(nbytes)
    if encoding == "base64":
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return raw.hex()


def generate_key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()


def generate_uuid() -> str:
    return str(uuid.uuid4())
