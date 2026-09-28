import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """Store algorithm, cost, salt and digest for future password verification."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=131072, r=8, p=1,
        maxmem=256 * 1024 * 1024, dklen=64,
    )
    return f"scrypt$131072$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify only our supported scrypt format, with bounded memory and CPU costs."""
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        return False
    if not isinstance(stored_hash, str) or len(stored_hash) != 179:
        return False
    try:
        algorithm, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
        if (algorithm, n, r, p) != ("scrypt", "131072", "8", "1"):
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 64:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=131072, r=8, p=1,
            maxmem=256 * 1024 * 1024, dklen=64,
        )
    except (ValueError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)
