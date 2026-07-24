import base64
import hashlib
import secrets

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token_enc: str) -> str:
    return _fernet().decrypt(token_enc.encode()).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def new_caldav_password() -> str:
    return secrets.token_urlsafe(24)


def new_caldav_username(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    safe = "".join(c if c.isalnum() else "-" for c in local).strip("-") or "user"
    return f"{safe}-{secrets.token_hex(3)}"
