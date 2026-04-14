from __future__ import annotations

import unittest
import asyncio
from unittest.mock import MagicMock, patch

import httpx
from jwt.exceptions import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from starlette.requests import Request

from api.app.core.auth import (
    authorize_claims_for_permissions,
    extract_bearer_token,
    extract_token_permissions,
    get_auth_verifier,
    normalize_token_claims,
    require_auth,
    require_permissions,
    require_realtime_access,
    validate_supabase_user_claims,
)
from api.app.core.config import settings
from api.app.core.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
)
from api.app.main import app
from api.tests.test_prediction_api import make_segment_payload


class StubRouteOptimizationApiService:
    def optimize_route(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        query_timestamp_unix: int,
    ):
        return type(
            "RouteResult",
            (),
            {
                "stops": [
                    {
                        "stop_id": str(origin_stop_id),
                        "stop_name": "Origin Stop",
                        "stop_lat": 28.70,
                        "stop_lon": 77.10,
                    },
                    {
                        "stop_id": str(destination_stop_id),
                        "stop_name": "Destination Stop",
                        "stop_lat": 28.71,
                        "stop_lon": 77.11,
                    },
                ],
                "segments": [
                    {
                        "route_id": "R1",
                        "from_stop_id": str(origin_stop_id),
                        "to_stop_id": str(destination_stop_id),
                        "stop_sequence": 1,
                        "normalized_stop_position": 1.0,
                        "distance_to_prev_stop_km": 1.2,
                        "scheduled_segment_minutes": 5.0,
                        "scheduled_wait_minutes_before_boarding": 0.0,
                        "wait_minutes_before_boarding": 0.0,
                        "boarding_feasibility_score": 0.95,
                        "travel_time_cost": 4.5,
                        "waiting_time_cost": 0.0,
                        "transfer_penalty_cost": 0.0,
                        "uncertainty_penalty_cost": 0.1,
                        "reliability_penalty_cost": 0.1,
                        "unstable_corridor_penalty_cost": 0.0,
                        "detour_penalty_cost": 0.0,
                        "fragile_transfer_penalty_cost": 0.0,
                        "generalized_cost": 4.7,
                        "congestion_proxy_ratio": 1.1,
                        "congestion_proxy_percent": 10.0,
                        "corridor_instability_score_live": 0.0,
                        "service_quality_score": 0.92,
                        "predicted_actual_segment_minutes": 4.5,
                        "predicted_segment_delay_minutes": -0.5,
                        "segment_uncertainty": 0.6,
                        "segment_reliability_score": 0.92,
                        "predicted_eta_lower_minutes": 3.9,
                        "predicted_eta_upper_minutes": 5.1,
                    }
                ],
                "total_predicted_eta_minutes": 4.5,
                "predicted_eta_lower_minutes": 3.9,
                "predicted_eta_upper_minutes": 5.1,
                "route_reliability_score": 0.92,
                "generalized_cost_minutes": 4.7,
                "total_wait_minutes": 0.0,
                "total_in_vehicle_minutes": 4.5,
                "transfer_count": 0,
                "fragile_transfer_count": 0,
                "transfer_fragility_score": 0.0,
                "congestion_proxy_ratio": 1.1,
                "congestion_proxy_percent": 10.0,
                "service_quality_score": 0.92,
                "selection_reasons": [
                    "Chosen for the lowest generalized cost balancing ETA, wait time, and risk."
                ],
                "explanation_summary": "Chosen for the lowest generalized cost balancing ETA, wait time, and risk.",
                "cost_breakdown": {
                    "travel_time_cost": 4.5,
                    "waiting_time_cost": 0.0,
                    "transfer_penalty_cost": 0.0,
                    "uncertainty_penalty_cost": 0.1,
                    "reliability_penalty_cost": 0.1,
                    "unstable_corridor_penalty_cost": 0.0,
                    "detour_penalty_cost": 0.0,
                    "fragile_transfer_penalty_cost": 0.0,
                    "generalized_cost": 4.7,
                },
                "alternatives": [],
            },
        )()


class StubRealtimeApiService:
    def refresh_vehicle_positions(self) -> dict:
        return {
            "fetched_snapshots": 3,
            "enriched_segments": 2,
            "latest_snapshot_time": 1743494825,
            "unmatched_snapshots": 1,
            "unmatched_trips": 1,
            "unmatched_vehicles": 1,
            "malformed_records": 0,
            "provider_format": "protobuf",
            "auth_mode": "query",
            "last_refresh_successful": True,
            "last_refresh_error": None,
        }

    def get_status(self) -> dict:
        return {
            "configured": True,
            "last_refresh_time": 1743494825,
            "last_successful_refresh_time": 1743494825,
            "latest_snapshot_time": 1743494825,
            "fetched_snapshots": 3,
            "enriched_segments": 2,
            "unmatched_snapshots": 1,
            "unmatched_trips": 1,
            "unmatched_vehicles": 1,
            "malformed_records": 0,
            "cached_segments": 2,
            "cached_vehicles": 1,
            "cache_max_age_seconds": 300,
            "cache_is_fresh": True,
            "provider_format": "protobuf",
            "auth_mode": "query",
            "last_refresh_successful": True,
            "last_refresh_error": None,
        }


class AuthDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        self.original_supabase_url = settings.SUPABASE_URL
        self.original_supabase_jwt_issuer = settings.SUPABASE_JWT_ISSUER
        self.original_supabase_jwt_audience = settings.SUPABASE_JWT_AUDIENCE
        self.original_supabase_jwt_algorithms = settings.SUPABASE_JWT_ALGORITHMS
        self.original_supabase_realtime_permission = (
            settings.SUPABASE_REALTIME_REQUIRED_PERMISSION
        )
        get_auth_verifier.cache_clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        settings.SUPABASE_URL = self.original_supabase_url
        settings.SUPABASE_JWT_ISSUER = self.original_supabase_jwt_issuer
        settings.SUPABASE_JWT_AUDIENCE = self.original_supabase_jwt_audience
        settings.SUPABASE_JWT_ALGORITHMS = self.original_supabase_jwt_algorithms
        settings.SUPABASE_REALTIME_REQUIRED_PERMISSION = (
            self.original_supabase_realtime_permission
        )
        get_auth_verifier.cache_clear()

    def test_require_auth_returns_disabled_claims_when_auth_is_off(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = False
        request = Request({"type": "http", "headers": []})

        claims = asyncio.run(require_auth(request))

        self.assertEqual(claims["sub"], "auth-disabled")

    def test_require_auth_rejects_missing_token_when_auth_is_on(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request({"type": "http", "headers": []})

        with self.assertRaises(AuthenticationException) as context:
            asyncio.run(require_auth(request))
        self.assertEqual(context.exception.status_code, 401)

    def test_require_auth_verifies_bearer_token(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer test-token")],
            }
        )
        verifier = MagicMock()
        verifier.verify_token.return_value = {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
        }

        with patch("api.app.core.auth.get_auth_verifier", return_value=verifier):
            claims = asyncio.run(require_auth(request))

        verifier.verify_token.assert_called_once_with("test-token")
        self.assertEqual(claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")

    def test_extract_bearer_token_rejects_malformed_authorization_header(self) -> None:
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Token test-token")],
            }
        )

        with self.assertRaises(AuthenticationException):
            extract_bearer_token(request)

    def test_require_auth_logs_malformed_authorization_header(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/auth/me",
                "headers": [(b"authorization", b"Token test-token")],
            }
        )

        with patch("api.app.core.auth.logger") as logger_mock:
            with self.assertRaises(AuthenticationException):
                asyncio.run(require_auth(request))

        logger_mock.warning.assert_called_once()
        self.assertIn("missing_or_malformed_bearer_token", logger_mock.warning.call_args[0][1])

    def test_normalize_token_claims_strips_subject_scope_and_permissions(self) -> None:
        claims = normalize_token_claims(
            {
                "sub": " 6c0a1808-4a95-4c21-85a8-44fa17c22d11 ",
                "role": " authenticated ",
                "session_id": " 6734ed6d-5101-4c88-958f-8eb6e2e27daf ",
                "scope": " route:read   realtime:manage ",
                "permissions": [" realtime:manage ", "", " route:read "],
                "app_metadata": {
                    "permissions": [" admin:read ", "", " realtime:manage "],
                },
            }
        )

        self.assertEqual(claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")
        self.assertEqual(claims["role"], "authenticated")
        self.assertEqual(claims["session_id"], "6734ed6d-5101-4c88-958f-8eb6e2e27daf")
        self.assertEqual(claims["scope"], "route:read realtime:manage")
        self.assertEqual(claims["permissions"], ["realtime:manage", "route:read"])
        self.assertEqual(
            claims["app_metadata"]["permissions"],
            ["admin:read", "realtime:manage"],
        )

    def test_validate_supabase_user_claims_rejects_non_user_tokens(self) -> None:
        with self.assertRaises(AuthenticationException) as context:
            validate_supabase_user_claims(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "anon",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                }
            )

        self.assertEqual(context.exception.status_code, 401)

    def test_validate_supabase_user_claims_rejects_anonymous_sessions(self) -> None:
        with self.assertRaises(AuthenticationException) as context:
            validate_supabase_user_claims(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "is_anonymous": True,
                }
            )

        self.assertEqual(context.exception.status_code, 401)

    def test_extract_token_permissions_combines_scope_and_permissions_claims(self) -> None:
        permissions = extract_token_permissions(
            {
                "scope": "route:read realtime:manage",
                "permissions": ["route:write", "realtime:manage"],
                "app_metadata": {"permissions": ["stops:read"]},
            }
        )

        self.assertEqual(
            permissions,
            {"route:read", "route:write", "realtime:manage", "stops:read"},
        )

    def test_missing_supabase_url_or_audience_raises_config_error(self) -> None:
        settings.SUPABASE_URL = ""
        settings.SUPABASE_JWT_AUDIENCE = ""

        with self.assertRaises(AuthConfigurationException) as context:
            get_auth_verifier()
        self.assertEqual(context.exception.status_code, 503)

    def test_require_auth_returns_service_error_when_jwks_lookup_fails(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer test-token")],
            }
        )

        with patch(
            "api.app.core.auth.get_auth_verifier",
            side_effect=AuthConfigurationException("Unable to retrieve Supabase signing keys."),
        ):
            with self.assertRaises(AuthConfigurationException) as context:
                    asyncio.run(require_auth(request))
        self.assertEqual(context.exception.status_code, 503)

    def test_supabase_verifier_rejects_invalid_audience(self) -> None:
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        verifier = get_auth_verifier()
        signing_key = type("SigningKey", (), {"key": "public-key"})()

        with patch("api.app.core.auth.get_jwks_client") as get_jwks_client_mock:
            get_jwks_client_mock.return_value.get_signing_key_from_jwt.return_value = signing_key

            with patch(
                "api.app.core.auth.jwt.decode",
                side_effect=InvalidAudienceError("Invalid audience"),
            ):
                with self.assertRaises(AuthenticationException) as context:
                    verifier.verify_token("test-token")

        self.assertEqual(context.exception.status_code, 401)

    def test_supabase_verifier_rejects_invalid_issuer(self) -> None:
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        verifier = get_auth_verifier()
        signing_key = type("SigningKey", (), {"key": "public-key"})()

        with patch("api.app.core.auth.get_jwks_client") as get_jwks_client_mock:
            get_jwks_client_mock.return_value.get_signing_key_from_jwt.return_value = signing_key

            with patch(
                "api.app.core.auth.jwt.decode",
                side_effect=InvalidIssuerError("Invalid issuer"),
            ):
                with self.assertRaises(AuthenticationException) as context:
                    verifier.verify_token("test-token")

        self.assertEqual(context.exception.status_code, 401)

    def test_supabase_verifier_rejects_expired_tokens(self) -> None:
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        verifier = get_auth_verifier()
        signing_key = type("SigningKey", (), {"key": "public-key"})()

        with patch("api.app.core.auth.get_jwks_client") as get_jwks_client_mock:
            get_jwks_client_mock.return_value.get_signing_key_from_jwt.return_value = signing_key

            with patch(
                "api.app.core.auth.jwt.decode",
                side_effect=ExpiredSignatureError("Token expired"),
            ):
                with self.assertRaises(AuthenticationException) as context:
                    verifier.verify_token("test-token")

        self.assertEqual(context.exception.status_code, 401)

    def test_require_auth_logs_invalid_access_token_failures(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/auth/me",
                "headers": [(b"authorization", b"Bearer invalid-token")],
            }
        )

        verifier = MagicMock()
        verifier.verify_token.side_effect = AuthenticationException(
            "Invalid or expired Supabase access token."
        )

        with patch("api.app.core.auth.get_auth_verifier", return_value=verifier):
            with patch("api.app.core.auth.logger") as logger_mock:
                with self.assertRaises(AuthenticationException):
                    asyncio.run(require_auth(request))

        logger_mock.warning.assert_called_once()
        self.assertIn("invalid_or_expired_access_token", logger_mock.warning.call_args[0][1])

    def test_require_auth_logs_jwks_or_config_failures(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_URL = "https://project.supabase.co"
        settings.SUPABASE_JWT_AUDIENCE = "authenticated"
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/auth/me",
                "headers": [(b"authorization", b"Bearer test-token")],
            }
        )

        with patch(
            "api.app.core.auth.get_auth_verifier",
            side_effect=AuthConfigurationException("Unable to retrieve Supabase signing keys."),
        ):
            with patch("api.app.core.auth.logger") as logger_mock:
                with self.assertRaises(AuthConfigurationException):
                    asyncio.run(require_auth(request))

        logger_mock.warning.assert_called_once()
        self.assertIn("auth_configuration_or_jwks_failure", logger_mock.warning.call_args[0][1])

    def test_require_realtime_access_rejects_missing_permission(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_REALTIME_REQUIRED_PERMISSION = "realtime:manage"

        with self.assertRaises(AuthorizationException) as context:
            asyncio.run(
                require_realtime_access(
                    {
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                        "app_metadata": {"permissions": ["route:read"]},
                    }
                )
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_require_realtime_access_accepts_supabase_app_metadata_permissions(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        settings.SUPABASE_REALTIME_REQUIRED_PERMISSION = "realtime:manage"

        app_metadata_claims = asyncio.run(
            require_realtime_access(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "app_metadata": {"permissions": ["realtime:manage"]},
                }
            )
        )
        legacy_permission_claims = asyncio.run(
            require_realtime_access(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "permissions": ["realtime:manage"],
                }
            )
        )

        self.assertEqual(app_metadata_claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")
        self.assertEqual(
            legacy_permission_claims["sub"],
            "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
        )

    def test_require_permissions_rejects_missing_permissions(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        route_access_guard = require_permissions(("route:read", "route:write"))

        with self.assertRaises(AuthorizationException) as context:
            asyncio.run(
                route_access_guard(
                    {
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                        "scope": "route:read",
                    }
                )
            )

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("route:write", context.exception.message)

    def test_authorize_claims_for_permissions_logs_missing_permissions(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/realtime/status",
                "headers": [],
            }
        )

        with patch("api.app.core.auth.logger") as logger_mock:
            with self.assertRaises(AuthorizationException):
                authorize_claims_for_permissions(
                    {
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                        "scope": "route:read",
                    },
                    ("realtime:manage",),
                    message="You do not have permission to access realtime operational endpoints.",
                    request=request,
                )

        logger_mock.warning.assert_called_once()
        self.assertIn("missing_permissions", logger_mock.warning.call_args[0][1])

    def test_require_permissions_accepts_permission_from_scope_or_permissions_claim(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        route_access_guard = require_permissions(("route:read",))

        scope_claims = asyncio.run(
            route_access_guard(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "scope": "route:read",
                }
            )
        )
        permissions_claims = asyncio.run(
            route_access_guard(
                {
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "permissions": ["route:read"],
                }
            )
        )

        self.assertEqual(scope_claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")
        self.assertEqual(permissions_claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")

    def test_require_permissions_rejects_empty_permission_configuration(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True
        empty_guard = require_permissions(("", "   "))

        with self.assertRaises(AuthConfigurationException) as context:
            asyncio.run(
                empty_guard(
                    {
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                        "scope": "route:read",
                    }
                )
            )

        self.assertEqual(context.exception.status_code, 503)

    def test_authorize_claims_for_permissions_accepts_valid_permissions(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = True

        claims = authorize_claims_for_permissions(
            {
                "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                "role": "authenticated",
                "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                "permissions": ["route:read"],
            },
            ("route:read",),
        )

        self.assertEqual(claims["sub"], "6c0a1808-4a95-4c21-85a8-44fa17c22d11")


class PublicApiAuthBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        settings.SUPABASE_AUTH_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        app.dependency_overrides.clear()

    async def _request(self, method: str, path: str, json_body: dict | None = None) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json_body)

    async def test_health_endpoint_remains_public(self) -> None:
        response = await self._request("GET", "/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    async def test_unversioned_health_endpoint_remains_public(self) -> None:
        response = await self._request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    async def test_prediction_endpoint_remains_public(self) -> None:
        response = await self._request(
            "POST",
            "/api/v1/predictions/segments",
            {"segments": [make_segment_payload()]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["predictions"]), 1)

    async def test_unversioned_prediction_endpoint_remains_public(self) -> None:
        response = await self._request(
            "POST",
            "/predictions/segments",
            {"segments": [make_segment_payload()]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["predictions"]), 1)

    async def test_route_optimization_endpoint_requires_authentication(self) -> None:
        payload = {
            "origin_stop_id": "A",
            "destination_stop_id": "B",
            "query_timestamp_unix": 1742803800,
        }

        response = await self._request("POST", "/api/v1/routes/optimize", payload)

        self.assertEqual(response.status_code, 401)

    async def test_unversioned_route_optimization_endpoint_requires_authentication(self) -> None:
        payload = {
            "origin_stop_id": "A",
            "destination_stop_id": "B",
            "query_timestamp_unix": 1742803800,
        }

        response = await self._request("POST", "/routes/optimize", payload)

        self.assertEqual(response.status_code, 401)

    async def test_authenticated_session_endpoint_requires_authentication(self) -> None:
        response = await self._request("GET", "/api/v1/auth/me")

        self.assertEqual(response.status_code, 401)

    async def test_unversioned_authenticated_session_endpoint_requires_authentication(self) -> None:
        response = await self._request("GET", "/auth/me")

        self.assertEqual(response.status_code, 401)

    async def test_authenticated_session_endpoint_returns_normalized_claims(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
            "azp": "frontend-client",
            "app_metadata": {"permissions": ["realtime:manage"]},
        }

        response = await self._request("GET", "/api/v1/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["subject"],
            "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
        )
        self.assertEqual(response.json()["scope"], [])
        self.assertEqual(
            response.json()["permissions"],
            ["realtime:manage"],
        )
        self.assertEqual(response.json()["claims"]["azp"], "frontend-client")

    async def test_route_optimization_endpoint_accepts_authenticated_requests(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
        }

        with patch(
            "api.app.api.v1.routes.get_route_optimization_service",
            return_value=StubRouteOptimizationApiService(),
        ):
            response = await self._request(
                "POST",
                "/api/v1/routes/optimize",
                {
                    "origin_stop_id": "A",
                    "destination_stop_id": "B",
                    "query_timestamp_unix": 1742803800,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_predicted_eta_minutes"], 4.5)

    async def test_realtime_endpoints_require_permissioned_authentication(self) -> None:
        refresh_response = await self._request("POST", "/api/v1/realtime/refresh")
        status_response = await self._request("GET", "/api/v1/realtime/status")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertEqual(status_response.status_code, 401)

    async def test_unversioned_realtime_endpoints_require_permissioned_authentication(self) -> None:
        refresh_response = await self._request("POST", "/realtime/refresh")
        status_response = await self._request("GET", "/realtime/status")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertEqual(status_response.status_code, 401)

    async def test_realtime_endpoints_accept_requests_with_required_permission(self) -> None:
        app.dependency_overrides[require_realtime_access] = lambda: {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
            "app_metadata": {"permissions": ["realtime:manage"]},
        }

        with patch(
            "api.app.api.v1.realtime.get_realtime_enrichment_service",
            return_value=StubRealtimeApiService(),
        ):
            refresh_response = await self._request("POST", "/api/v1/realtime/refresh")
            status_response = await self._request("GET", "/api/v1/realtime/status")

        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()["configured"])


if __name__ == "__main__":
    unittest.main()
