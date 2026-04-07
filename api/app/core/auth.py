from __future__ import annotations

from functools import lru_cache
import logging
from typing import Any, Callable, TypeAlias

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


TokenClaims: TypeAlias = dict[str, Any]
PermissionResolver: TypeAlias = Callable[[], tuple[str, ...]]

logger = logging.getLogger(__name__)


def describe_request(request: Request | None) -> str:
    if request is None:
        return "<unknown-request>"
    method = request.scope.get("method") or "<unknown-method>"
    path = request.scope.get("path") or request.scope.get("root_path") or "<unknown-path>"
    return f"{method} {path}"


def log_auth_warning(
    event: str,
    *,
    request: Request | None = None,
    subject: str | None = None,
    detail: str | None = None,
    required_permissions: tuple[str, ...] | None = None,
    token_permissions: set[str] | None = None,
) -> None:
    message_parts = [f"event={event}", f"request={describe_request(request)}"]
    if subject:
        message_parts.append(f"subject={subject}")
    if detail:
        message_parts.append(f"detail={detail}")
    if required_permissions:
        message_parts.append(
            "required_permissions=" + ",".join(sorted(required_permissions))
        )
    if token_permissions is not None:
        message_parts.append(
            "token_permissions=" + ",".join(sorted(token_permissions))
        )
    logger.warning("Auth warning: %s", " | ".join(message_parts))


@lru_cache(maxsize=4)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


class SupabaseJWTVerifier:
    def __init__(
        self,
        *,
        project_url: str,
        audience: str,
        issuer: str,
        algorithms: tuple[str, ...],
    ):
        normalized_project_url = project_url.strip().rstrip("/")
        if not normalized_project_url:
            raise AuthConfigurationException("SUPABASE_URL is not configured.")
        if not audience:
            raise AuthConfigurationException("SUPABASE_JWT_AUDIENCE is not configured.")
        normalized_issuer = issuer.strip().rstrip("/")
        if not normalized_issuer:
            raise AuthConfigurationException("SUPABASE_JWT_ISSUER is not configured.")

        self.project_url = normalized_project_url
        self.audience = audience
        self.issuer = normalized_issuer
        self.algorithms = algorithms
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"

    def verify_token(self, token: str) -> dict:
        try:
            signing_key = get_jwks_client(self.jwks_url).get_signing_key_from_jwt(token)
        except PyJWKClientError as exc:
            raise AuthConfigurationException(
                "Unable to retrieve Supabase signing keys."
            ) from exc
        except InvalidTokenError as exc:
            raise AuthenticationException("Invalid or expired Supabase access token.") from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Supabase token verification service is unavailable."
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
            raise AuthenticationException("Invalid or expired Supabase access token.") from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Supabase token verification service is unavailable."
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


def authorize_claims_for_permissions(
    claims: TokenClaims,
    required_permissions: tuple[str, ...] | PermissionResolver,
    *,
    message: str | None = None,
    request: Request | None = None,
) -> TokenClaims:
    if not settings.auth_enabled:
        return claims

    normalized_permissions = resolve_required_permissions(required_permissions)
    token_permissions = extract_token_permissions(claims)
    missing_permissions = [
        permission
        for permission in normalized_permissions
        if permission not in token_permissions
    ]

    if missing_permissions:
        subject = str(claims.get("sub") or "")
        log_auth_warning(
            "missing_permissions",
            request=request,
            subject=subject or None,
            detail=message,
            required_permissions=normalized_permissions,
            token_permissions=token_permissions,
        )
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


def get_realtime_required_permissions() -> tuple[str, ...]:
    required_permission = settings.realtime_required_permission.strip()
    if not required_permission:
        raise AuthConfigurationException(
            "SUPABASE_REALTIME_REQUIRED_PERMISSION is not configured."
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
        request: Request = None,
    ) -> TokenClaims:
        return authorize_claims_for_permissions(
            claims,
            required_permissions,
            message=message,
            request=request,
        )

    return dependency

@lru_cache(maxsize=1)
def get_auth_verifier() -> SupabaseJWTVerifier:
    issuer = settings.auth_jwt_issuer.strip()
    algorithms = tuple(
        value.strip()
        for value in settings.auth_jwt_algorithms.split(",")
        if value.strip()
    ) or ("RS256",)
    return SupabaseJWTVerifier(
        project_url=settings.auth_project_url,
        audience=settings.auth_jwt_audience,
        issuer=issuer,
        algorithms=algorithms,
    )


def get_auth0_verifier() -> SupabaseJWTVerifier:
    return get_auth_verifier()


get_auth0_verifier.cache_clear = get_auth_verifier.cache_clear  # type: ignore[attr-defined]

async def require_auth(
    request: Request,
) -> TokenClaims:
    if not settings.auth_enabled:
        return {"sub": "auth-disabled"}

    try:
        token = extract_bearer_token(request)
    except AuthenticationException:
        log_auth_warning(
            "missing_or_malformed_bearer_token",
            request=request,
            detail="Authorization header must contain a Bearer token.",
        )
        raise

    try:
        verifier = get_auth_verifier()
        return normalize_token_claims(verifier.verify_token(token))
    except AuthenticationException as exc:
        log_auth_warning(
            "invalid_or_expired_access_token",
            request=request,
            detail=exc.message,
        )
        raise
    except AuthConfigurationException as exc:
        log_auth_warning(
            "auth_configuration_or_jwks_failure",
            request=request,
            detail=exc.message,
        )
        raise


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
