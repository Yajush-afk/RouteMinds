from __future__ import annotations

import unittest
import asyncio
from unittest.mock import MagicMock, patch

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from api.app.core.auth import get_auth0_verifier, require_auth
from api.app.core.config import settings
from api.app.main import app
from api.tests.test_prediction_api import make_segment_payload


class AuthDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_auth0_enabled = settings.AUTH0_ENABLED
        self.original_auth0_domain = settings.AUTH0_DOMAIN
        self.original_auth0_audience = settings.AUTH0_AUDIENCE
        self.original_auth0_issuer = settings.AUTH0_ISSUER
        self.original_auth0_algorithms = settings.AUTH0_ALGORITHMS
        get_auth0_verifier.cache_clear()

    def tearDown(self) -> None:
        settings.AUTH0_ENABLED = self.original_auth0_enabled
        settings.AUTH0_DOMAIN = self.original_auth0_domain
        settings.AUTH0_AUDIENCE = self.original_auth0_audience
        settings.AUTH0_ISSUER = self.original_auth0_issuer
        settings.AUTH0_ALGORITHMS = self.original_auth0_algorithms
        get_auth0_verifier.cache_clear()

    def test_require_auth_returns_disabled_claims_when_auth_is_off(self) -> None:
        settings.AUTH0_ENABLED = False
        request = Request({"type": "http", "headers": []})

        claims = asyncio.run(require_auth(request))

        self.assertEqual(claims["sub"], "auth-disabled")

    def test_require_auth_rejects_missing_token_when_auth_is_on(self) -> None:
        settings.AUTH0_ENABLED = True
        request = Request({"type": "http", "headers": []})

        with self.assertRaises(HTTPException) as context:
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

    def test_missing_auth0_domain_or_audience_raises_config_error(self) -> None:
        settings.AUTH0_DOMAIN = ""
        settings.AUTH0_AUDIENCE = ""

        with self.assertRaises(HTTPException) as context:
            get_auth0_verifier()
        self.assertEqual(context.exception.status_code, 503)


class PublicApiAuthBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_auth0_enabled = settings.AUTH0_ENABLED
        settings.AUTH0_ENABLED = True

    def tearDown(self) -> None:
        settings.AUTH0_ENABLED = self.original_auth0_enabled

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

    async def test_prediction_endpoint_remains_public(self) -> None:
        response = await self._request(
            "POST",
            "/api/v1/predictions/segments",
            {"segments": [make_segment_payload()]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["predictions"]), 1)


if __name__ == "__main__":
    unittest.main()
