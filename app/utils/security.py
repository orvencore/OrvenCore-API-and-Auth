import hashlib
import secrets


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def create_secret(prefix: str = "") -> str:
    token = secrets.token_urlsafe(36)
    return f"{prefix}{token}" if prefix else token

