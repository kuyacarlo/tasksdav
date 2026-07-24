import base64
import hashlib
import secrets

import bcrypt
from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token_enc: str) -> str:
    return _fernet().decrypt(token_enc.encode()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def new_caldav_password() -> str:
    return secrets.token_urlsafe(24)


def new_caldav_username(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    safe = "".join(c if c.isalnum() else "-" for c in local).strip("-") or "user"
    return f"{safe}-{secrets.token_hex(3)}"
