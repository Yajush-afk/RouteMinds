from __future__ import annotations

import unittest
import asyncio
from unittest.mock import MagicMock, patch

import httpx
from starlette.requests import Request

from api.app.core.auth import (
    extract_bearer_token,
    extract_token_permissions,
    get_auth0_verifier,
    normalize_token_claims,
    require_auth,
    require_permissions,
    require_realtime_access,
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
                        "predicted_actual_segment_minutes": 4.5,
                        "predicted_segment_delay_minutes": -0.5,
                    }
                ],
                "total_predicted_eta_minutes": 4.5,
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
        self.original_auth0_enabled = settings.AUTH0_ENABLED
        self.original_auth0_domain = settings.AUTH0_DOMAIN
        self.original_auth0_audience = settings.AUTH0_AUDIENCE
        self.original_auth0_issuer = settings.AUTH0_ISSUER
        self.original_auth0_algorithms = settings.AUTH0_ALGORITHMS
        self.original_auth0_realtime_permission = settings.AUTH0_REALTIME_REQUIRED_PERMISSION
        get_auth0_verifier.cache_clear()

    def tearDown(self) -> None:
        settings.AUTH0_ENABLED = self.original_auth0_enabled
        settings.AUTH0_DOMAIN = self.original_auth0_domain
        settings.AUTH0_AUDIENCE = self.original_auth0_audience
        settings.AUTH0_ISSUER = self.original_auth0_issuer
        settings.AUTH0_ALGORITHMS = self.original_auth0_algorithms
        settings.AUTH0_REALTIME_REQUIRED_PERMISSION = self.original_auth0_realtime_permission
        get_auth0_verifier.cache_clear()

    def test_require_auth_returns_disabled_claims_when_auth_is_off(self) -> None:
        settings.AUTH0_ENABLED = False
        request = Request({"type": "http", "headers": []})

        claims = asyncio.run(require_auth(request))

        self.assertEqual(claims["sub"], "auth-disabled")

    def test_require_auth_rejects_missing_token_when_auth_is_on(self) -> None:
        settings.AUTH0_ENABLED = True
        request = Request({"type": "http", "headers": []})

        with self.assertRaises(AuthenticationException) as context:
            asyncio.run(require_auth(request))
        self.assertEqual(context.exception.status_code, 401)

    def test_require_auth_verifies_bearer_token(self) -> None:
        settings.AUTH0_ENABLED = True
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer test-token")],
            }
        )
        verifier = MagicMock()
        verifier.verify_token.return_value = {"sub": "auth0|user-123"}

        with patch("api.app.core.auth.get_auth0_verifier", return_value=verifier):
            claims = asyncio.run(require_auth(request))

        verifier.verify_token.assert_called_once_with("test-token")
        self.assertEqual(claims["sub"], "auth0|user-123")

    def test_extract_bearer_token_rejects_malformed_authorization_header(self) -> None:
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Token test-token")],
            }
        )

        with self.assertRaises(AuthenticationException):
            extract_bearer_token(request)

    def test_normalize_token_claims_strips_subject_scope_and_permissions(self) -> None:
        claims = normalize_token_claims(
            {
                "sub": " auth0|user-123 ",
                "scope": " route:read   realtime:manage ",
                "permissions": [" realtime:manage ", "", " route:read "],
            }
        )

        self.assertEqual(claims["sub"], "auth0|user-123")
        self.assertEqual(claims["scope"], "route:read realtime:manage")
        self.assertEqual(claims["permissions"], ["realtime:manage", "route:read"])

    def test_extract_token_permissions_combines_scope_and_permissions_claims(self) -> None:
        permissions = extract_token_permissions(
            {
                "scope": "route:read realtime:manage",
                "permissions": ["route:write", "realtime:manage"],
            }
        )

        self.assertEqual(
            permissions,
            {"route:read", "route:write", "realtime:manage"},
        )

    def test_missing_auth0_domain_or_audience_raises_config_error(self) -> None:
        settings.AUTH0_DOMAIN = ""
        settings.AUTH0_AUDIENCE = ""

        with self.assertRaises(AuthConfigurationException) as context:
            get_auth0_verifier()
        self.assertEqual(context.exception.status_code, 503)

    def test_require_auth_returns_service_error_when_jwks_lookup_fails(self) -> None:
        settings.AUTH0_ENABLED = True
        settings.AUTH0_DOMAIN = "tenant.auth0.com"
        settings.AUTH0_AUDIENCE = "routeminds-api"
        request = Request(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer test-token")],
            }
        )

        with patch(
            "api.app.core.auth.get_auth0_verifier",
            side_effect=AuthConfigurationException("Unable to retrieve Auth0 signing keys."),
        ):
            with self.assertRaises(AuthConfigurationException) as context:
                asyncio.run(require_auth(request))
        self.assertEqual(context.exception.status_code, 503)

    def test_require_realtime_access_rejects_missing_permission(self) -> None:
        settings.AUTH0_ENABLED = True
        settings.AUTH0_REALTIME_REQUIRED_PERMISSION = "realtime:manage"

        with self.assertRaises(AuthorizationException) as context:
            asyncio.run(require_realtime_access({"sub": "auth0|user", "scope": "route:read"}))
        self.assertEqual(context.exception.status_code, 403)

    def test_require_realtime_access_accepts_scope_or_permissions_claim(self) -> None:
        settings.AUTH0_ENABLED = True
        settings.AUTH0_REALTIME_REQUIRED_PERMISSION = "realtime:manage"

        scope_claims = asyncio.run(
            require_realtime_access({"sub": "auth0|user", "scope": "route:read realtime:manage"})
        )
        permission_claims = asyncio.run(
            require_realtime_access(
                {"sub": "auth0|user", "permissions": ["realtime:manage"]}
            )
        )

        self.assertEqual(scope_claims["sub"], "auth0|user")
        self.assertEqual(permission_claims["sub"], "auth0|user")

    def test_require_permissions_rejects_missing_permissions(self) -> None:
        settings.AUTH0_ENABLED = True
        route_access_guard = require_permissions(("route:read", "route:write"))

        with self.assertRaises(AuthorizationException) as context:
            asyncio.run(route_access_guard({"sub": "auth0|user", "scope": "route:read"}))

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("route:write", context.exception.message)

    def test_require_permissions_accepts_permission_from_scope_or_permissions_claim(self) -> None:
        settings.AUTH0_ENABLED = True
        route_access_guard = require_permissions(("route:read",))

        scope_claims = asyncio.run(
            route_access_guard({"sub": "auth0|user", "scope": "route:read"})
        )
        permissions_claims = asyncio.run(
            route_access_guard({"sub": "auth0|user", "permissions": ["route:read"]})
        )

        self.assertEqual(scope_claims["sub"], "auth0|user")
        self.assertEqual(permissions_claims["sub"], "auth0|user")

    def test_require_permissions_rejects_empty_permission_configuration(self) -> None:
        settings.AUTH0_ENABLED = True
        empty_guard = require_permissions(("", "   "))

        with self.assertRaises(AuthConfigurationException) as context:
            asyncio.run(empty_guard({"sub": "auth0|user", "scope": "route:read"}))

        self.assertEqual(context.exception.status_code, 503)


class PublicApiAuthBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_auth0_enabled = settings.AUTH0_ENABLED
        settings.AUTH0_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.AUTH0_ENABLED = self.original_auth0_enabled
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

    async def test_route_optimization_endpoint_accepts_authenticated_requests(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {"sub": "auth0|contract-user"}

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
            "sub": "auth0|contract-user",
            "permissions": ["realtime:manage"],
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
