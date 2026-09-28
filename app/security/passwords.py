import hashlib
import secrets


def hash_password(password: str) -> str:
    """Store algorithm, cost, salt and digest for future password verification."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=131072, r=8, p=1,
        maxmem=256 * 1024 * 1024, dklen=64,
    )
    return f"scrypt$131072$8$1${salt.hex()}${digest.hex()}"
