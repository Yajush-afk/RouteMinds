from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, Request
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import PyJWKClientError

from api.app.core.config import settings
from api.app.core.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
)

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
            raise AuthConfigurationException("AUTH0_DOMAIN is not configured.")
        if not audience:
            raise AuthConfigurationException("AUTH0_AUDIENCE is not configured.")

        self.domain = normalized_domain
        self.audience = audience
        self.issuer = issuer
        self.algorithms = algorithms
        self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"

    def verify_token(self, token: str) -> dict:
        try:
            signing_key = get_jwks_client(self.jwks_url).get_signing_key_from_jwt(token)
        except PyJWKClientError as exc:
            raise AuthConfigurationException(
                "Unable to retrieve Auth0 signing keys."
            ) from exc
        except InvalidTokenError as exc:
            raise AuthenticationException("Invalid or expired Auth0 access token.") from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Auth0 token verification service is unavailable."
            ) from exc

        try:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
            )
        except InvalidTokenError as exc:
            raise AuthenticationException("Invalid or expired Auth0 access token.") from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Auth0 token verification service is unavailable."
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
        raise AuthenticationException()

    verifier = get_auth0_verifier()
    return verifier.verify_token(token.strip())

def extract_token_permissions(claims: dict) -> set[str]:
    permissions: set[str] = set()

    raw_permissions = claims.get("permissions")
    if isinstance(raw_permissions, list):
        permissions.update(str(value).strip() for value in raw_permissions if str(value).strip())

    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        permissions.update(value.strip() for value in raw_scope.split() if value.strip())

    return permissions


async def require_realtime_access(
    claims: dict = Depends(require_auth),
) -> dict:
    if not settings.AUTH0_ENABLED:
        return claims

    required_permission = settings.AUTH0_REALTIME_REQUIRED_PERMISSION.strip()
    if not required_permission:
        raise AuthConfigurationException(
            "AUTH0_REALTIME_REQUIRED_PERMISSION is not configured."
        )

    permissions = extract_token_permissions(claims)
    if required_permission not in permissions:
        raise AuthorizationException(
            "You do not have permission to access realtime operational endpoints."
        )

    return claims
