from __future__ import annotations

import base64
import hashlib
import hmac
import os

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 32


def generate_password_salt() -> str:
    """Return a URL-safe salt for password hashing."""
    return base64.urlsafe_b64encode(os.urandom(SALT_BYTES)).decode("ascii")


def hash_password(password: str, salt: str) -> str:
    if not isinstance(password, str) or password == "":
        raise ValueError("密码不能为空")
    if not salt:
        raise ValueError("密码盐不能为空")

    derived_key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    encoded_hash = base64.urlsafe_b64encode(derived_key).decode("ascii")
    return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${encoded_hash}"


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    if not password or not salt or not expected_hash:
        return False

    try:
        actual_hash = hash_password(password, salt)
    except ValueError:
        return False
    return hmac.compare_digest(actual_hash, expected_hash)
