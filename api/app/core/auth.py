from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError, PyJWKClient

from api.app.core.config import settings

def normalize_auth0_domain(domain: str) -> str:
    value = domain.strip()
    if value.startswith("https://"):
        value = value[len("https://") :]
    return value.rstrip("/")


@lru_cache(maxsize=4)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


class Auth0JWTVerifier:
    def __init__(
        self,
        *,
        domain: str,
        audience: str,
        issuer: str,
        algorithms: tuple[str, ...],
    ):
        normalized_domain = normalize_auth0_domain(domain)
        if not normalized_domain:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AUTH0_DOMAIN is not configured.",
            )
        if not audience:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AUTH0_AUDIENCE is not configured.",
            )

        self.domain = normalized_domain
        self.audience = audience
        self.issuer = issuer
        self.algorithms = algorithms
        self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"

    def verify_token(self, token: str) -> dict:
        try:
            signing_key = get_jwks_client(self.jwks_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
            )
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Auth0 access token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to validate Auth0 access token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

@lru_cache(maxsize=1)
def get_auth0_verifier() -> Auth0JWTVerifier:
    issuer = settings.AUTH0_ISSUER.strip() or f"https://{normalize_auth0_domain(settings.AUTH0_DOMAIN)}/"
    algorithms = tuple(
        value.strip()
        for value in settings.AUTH0_ALGORITHMS.split(",")
        if value.strip()
    ) or ("RS256",)
    return Auth0JWTVerifier(
        domain=settings.AUTH0_DOMAIN,
        audience=settings.AUTH0_AUDIENCE,
        issuer=issuer,
        algorithms=algorithms,
    )

async def require_auth(
    request: Request,
) -> dict:
    if not settings.AUTH0_ENABLED:
        return {"sub": "auth-disabled"}

    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier = get_auth0_verifier()
    return verifier.verify_token(token.strip())
