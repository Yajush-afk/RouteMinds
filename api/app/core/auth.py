from __future__ import annotations

import json
from functools import lru_cache
import logging
from typing import Any, Callable, TypeAlias

import jwt
from fastapi import Depends, Request
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    PyJWKClientError,
)

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
    reason_code: str | None = None,
    required_permissions: tuple[str, ...] | None = None,
    token_permissions: set[str] | None = None,
    auth_metadata: dict[str, str] | None = None,
    expected_issuer: str | None = None,
    expected_audience: str | None = None,
) -> None:
    message_parts = [f"event={event}", f"request={describe_request(request)}"]
    if subject:
        message_parts.append(f"subject={subject}")
    if detail:
        message_parts.append(f"detail={detail}")
    if reason_code:
        message_parts.append(f"reason_code={reason_code}")
    if required_permissions:
        message_parts.append(
            "required_permissions=" + ",".join(sorted(required_permissions))
        )
    if token_permissions is not None:
        message_parts.append(
            "token_permissions=" + ",".join(sorted(token_permissions))
        )
    if expected_issuer:
        message_parts.append(f"expected_issuer={expected_issuer}")
    if expected_audience:
        message_parts.append(f"expected_audience={expected_audience}")
    if auth_metadata:
        for key in sorted(auth_metadata):
            message_parts.append(f"{key}={auth_metadata[key]}")
    logger.warning("Auth warning: %s", " | ".join(message_parts))


@lru_cache(maxsize=4)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _classify_jwks_error(exc: PyJWKClientError) -> tuple[str, bool]:
    normalized_message = str(exc).strip().lower()
    if (
        "unable to find a signing key" in normalized_message
        or "matching the kid" in normalized_message
        or "signing key" in normalized_message
    ):
        return ("signing_key_not_found", True)
    return ("jwks_fetch_failed", False)


def _stringify_token_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, bool):
            return None
        return str(value)
    if isinstance(value, str):
        normalized_value = value.strip()
        return normalized_value or None
    if isinstance(value, list):
        normalized_items = [
            str(item).strip() for item in value if str(item).strip()
        ]
        if normalized_items:
            return ",".join(normalized_items)
    if isinstance(value, dict):
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            return None
    return None


def extract_safe_token_metadata(token: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    parts = token.split(".")
    metadata["token_segments"] = str(len(parts))

    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        header = None

    if isinstance(header, dict):
        for source_key, metadata_key in (
            ("alg", "token_alg"),
            ("kid", "token_kid"),
            ("typ", "token_typ"),
        ):
            value = _stringify_token_value(header.get(source_key))
            if value is not None:
                metadata[metadata_key] = value

    try:
        claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except Exception:
        claims = None

    if isinstance(claims, dict):
        for source_key, metadata_key in (
            ("iss", "token_iss"),
            ("aud", "token_aud"),
            ("sub", "token_sub"),
            ("role", "token_role"),
            ("exp", "token_exp"),
            ("iat", "token_iat"),
            ("nbf", "token_nbf"),
        ):
            value = _stringify_token_value(claims.get(source_key))
            if value is not None:
                metadata[metadata_key] = value

        metadata["token_session_id_present"] = (
            "true" if bool(_stringify_token_value(claims.get("session_id"))) else "false"
        )
        if claims.get("is_anonymous") is True:
            metadata["token_is_anonymous"] = "true"

    return metadata


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
            reason_code, is_auth_failure = _classify_jwks_error(exc)
            if is_auth_failure:
                raise AuthenticationException(
                    "Invalid or expired Supabase access token.",
                    reason_code=reason_code,
                ) from exc
            raise AuthConfigurationException(
                "Unable to retrieve Supabase signing keys.",
                reason_code=reason_code,
            ) from exc
        except DecodeError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="malformed_token",
            ) from exc
        except InvalidTokenError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="invalid_token_generic",
            ) from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Supabase token verification service is unavailable.",
                reason_code="verifier_unavailable",
            ) from exc

        try:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
            )
        except ExpiredSignatureError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="token_expired",
            ) from exc
        except InvalidAudienceError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="invalid_audience",
            ) from exc
        except InvalidIssuerError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="invalid_issuer",
            ) from exc
        except ImmatureSignatureError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="token_not_yet_valid",
            ) from exc
        except DecodeError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="invalid_signature",
            ) from exc
        except InvalidTokenError as exc:
            raise AuthenticationException(
                "Invalid or expired Supabase access token.",
                reason_code="invalid_token_generic",
            ) from exc
        except Exception as exc:
            raise AuthConfigurationException(
                "Supabase token verification service is unavailable.",
                reason_code="verifier_unavailable",
            ) from exc


def normalize_token_claims(claims: TokenClaims) -> TokenClaims:
    normalized_claims = dict(claims)

    subject = normalized_claims.get("sub")
    if subject is not None:
        normalized_claims["sub"] = str(subject).strip()

    role = normalized_claims.get("role")
    if role is not None:
        normalized_claims["role"] = str(role).strip()

    session_id = normalized_claims.get("session_id")
    if session_id is not None:
        normalized_claims["session_id"] = str(session_id).strip()

    scope = normalized_claims.get("scope")
    if isinstance(scope, str):
        normalized_claims["scope"] = " ".join(
            value.strip() for value in scope.split() if value.strip()
        )

    app_metadata = normalized_claims.get("app_metadata")
    if isinstance(app_metadata, dict):
        normalized_app_metadata = dict(app_metadata)
        app_permissions = normalized_app_metadata.get("permissions")
        if isinstance(app_permissions, list):
            normalized_app_metadata["permissions"] = [
                str(value).strip() for value in app_permissions if str(value).strip()
            ]
        normalized_claims["app_metadata"] = normalized_app_metadata

    permissions = normalized_claims.get("permissions")
    if isinstance(permissions, list):
        normalized_claims["permissions"] = [
            str(value).strip() for value in permissions if str(value).strip()
        ]

    return normalized_claims


def validate_supabase_user_claims(claims: TokenClaims) -> TokenClaims:
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise AuthenticationException(
            "Supabase access token is missing the user subject claim.",
            reason_code="missing_sub",
        )

    role = str(claims.get("role") or "").strip()
    if role != "authenticated":
        raise AuthenticationException(
            "Supabase access token is not a user session token.",
            reason_code="invalid_role",
        )

    session_id = str(claims.get("session_id") or "").strip()
    if not session_id:
        raise AuthenticationException(
            "Supabase access token is missing the session_id claim.",
            reason_code="missing_session_id",
        )

    if claims.get("is_anonymous") is True:
        raise AuthenticationException(
            "Anonymous Supabase sessions are not allowed for this API.",
            reason_code="anonymous_session",
        )

    return claims


def extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationException(reason_code="missing_bearer_token")
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

async def require_auth(
    request: Request,
) -> TokenClaims:
    if not settings.auth_enabled:
        return {"sub": "auth-disabled"}

    try:
        token = extract_bearer_token(request)
    except AuthenticationException as exc:
        log_auth_warning(
            "missing_or_malformed_bearer_token",
            request=request,
            detail="Authorization header must contain a Bearer token.",
            reason_code=exc.reason_code,
        )
        raise

    token_metadata = extract_safe_token_metadata(token)

    try:
        verifier = get_auth_verifier()
        claims = normalize_token_claims(verifier.verify_token(token))
        return validate_supabase_user_claims(claims)
    except AuthenticationException as exc:
        log_auth_warning(
            "invalid_or_expired_access_token",
            request=request,
            subject=_stringify_token_value(token_metadata.get("token_sub")),
            detail=exc.message,
            reason_code=exc.reason_code,
            auth_metadata=token_metadata,
            expected_issuer=settings.auth_jwt_issuer.strip() or None,
            expected_audience=settings.auth_jwt_audience.strip() or None,
        )
        raise
    except AuthConfigurationException as exc:
        log_auth_warning(
            "auth_configuration_or_jwks_failure",
            request=request,
            detail=exc.message,
            reason_code=exc.reason_code,
            auth_metadata=token_metadata,
            expected_issuer=settings.auth_jwt_issuer.strip() or None,
            expected_audience=settings.auth_jwt_audience.strip() or None,
        )
        raise


def extract_token_permissions(claims: TokenClaims) -> set[str]:
    permissions: set[str] = set()

    app_metadata = claims.get("app_metadata")
    if isinstance(app_metadata, dict):
        raw_app_permissions = app_metadata.get("permissions")
        if isinstance(raw_app_permissions, list):
            permissions.update(
                str(value).strip() for value in raw_app_permissions if str(value).strip()
            )

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
