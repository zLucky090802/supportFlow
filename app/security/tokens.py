import os
from datetime import datetime, timezone

import jwt

from app.exceptions.auth_exceptions import AuthenticationError, AuthConfigurationError


ACCESS_TOKEN_EXPIRE_SECONDS = 30 * 60
JWT_ISSUER = "supportflow"
JWT_AUDIENCE = "supportflow-api"


def _secret_key() -> str:
    key = os.getenv("JWT_SECRET_KEY", "")
    if len(key.encode("utf-8")) < 32 or not key.strip():
        raise AuthConfigurationError()
    return key


def create_access_token(user_id: str) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
         "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "type": "access"},
        _secret_key(), algorithm="HS256",
    )


def decode_access_token(token: str) -> str:
    key = _secret_key()
    if not token or len(token) > 4096:
        raise AuthenticationError()
    try:
        claims = jwt.decode(
            token, key, algorithms=["HS256"], issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "iat", "exp", "iss", "aud", "type"]},
        )
        if (
            claims["type"] != "access"
            or not isinstance(claims["sub"], str)
            or not claims["sub"].strip()
            or len(claims["sub"]) > 36
            or type(claims["iat"]) is not int
            or type(claims["exp"]) is not int
            or not 0 < claims["exp"] - claims["iat"] <= ACCESS_TOKEN_EXPIRE_SECONDS
        ):
            raise AuthenticationError()
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise AuthenticationError() from None
    return claims["sub"]
