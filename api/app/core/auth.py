from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, TypeAlias

import jwt
from fastapi import Depends, Request
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import PyJWKClientError

from api.app.core.config import normalize_auth0_domain, settings
from api.app.core.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
)


TokenClaims: TypeAlias = dict[str, Any]
PermissionResolver: TypeAlias = Callable[[], tuple[str, ...]]


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


def normalize_token_claims(claims: TokenClaims) -> TokenClaims:
    normalized_claims = dict(claims)

    subject = normalized_claims.get("sub")
    if subject is not None:
        normalized_claims["sub"] = str(subject).strip()

    scope = normalized_claims.get("scope")
    if isinstance(scope, str):
        normalized_claims["scope"] = " ".join(
            value.strip() for value in scope.split() if value.strip()
        )

    permissions = normalized_claims.get("permissions")
    if isinstance(permissions, list):
        normalized_claims["permissions"] = [
            str(value).strip() for value in permissions if str(value).strip()
        ]

    return normalized_claims


def extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationException()
    return token.strip()


def normalize_required_permissions(required_permissions: tuple[str, ...]) -> tuple[str, ...]:
    normalized_permissions = tuple(
        permission.strip() for permission in required_permissions if permission.strip()
    )
    if not normalized_permissions:
        raise AuthConfigurationException(
            "At least one required permission must be configured for this endpoint."
        )
    return normalized_permissions


def get_realtime_required_permissions() -> tuple[str, ...]:
    required_permission = settings.AUTH0_REALTIME_REQUIRED_PERMISSION.strip()
    if not required_permission:
        raise AuthConfigurationException(
            "AUTH0_REALTIME_REQUIRED_PERMISSION is not configured."
        )
    return (required_permission,)


def resolve_required_permissions(
    required_permissions: tuple[str, ...] | PermissionResolver,
) -> tuple[str, ...]:
    if callable(required_permissions):
        return normalize_required_permissions(required_permissions())
    return normalize_required_permissions(required_permissions)


def require_permissions(
    required_permissions: tuple[str, ...] | PermissionResolver,
    *,
    message: str | None = None,
):
    async def dependency(
        claims: TokenClaims = Depends(require_auth),
    ) -> TokenClaims:
        if not settings.AUTH0_ENABLED:
            return claims

        normalized_permissions = resolve_required_permissions(required_permissions)
        token_permissions = extract_token_permissions(claims)
        missing_permissions = [
            permission
            for permission in normalized_permissions
            if permission not in token_permissions
        ]

        if missing_permissions:
            if message is not None:
                raise AuthorizationException(message)
            if len(missing_permissions) == 1:
                raise AuthorizationException(
                    f"You do not have the required permission: {missing_permissions[0]}."
                )
            raise AuthorizationException(
                "You do not have the required permissions: "
                + ", ".join(missing_permissions)
                + "."
            )

        return claims

    return dependency

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
) -> TokenClaims:
    if not settings.AUTH0_ENABLED:
        return {"sub": "auth-disabled"}

    verifier = get_auth0_verifier()
    return normalize_token_claims(verifier.verify_token(extract_bearer_token(request)))


def extract_token_permissions(claims: TokenClaims) -> set[str]:
    permissions: set[str] = set()

    raw_permissions = claims.get("permissions")
    if isinstance(raw_permissions, list):
        permissions.update(str(value).strip() for value in raw_permissions if str(value).strip())

    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        permissions.update(value.strip() for value in raw_scope.split() if value.strip())

    return permissions


require_realtime_access = require_permissions(
    get_realtime_required_permissions,
    message="You do not have permission to access realtime operational endpoints.",
)
