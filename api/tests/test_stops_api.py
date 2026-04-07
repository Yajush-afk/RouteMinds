from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from api.app.core.auth import require_auth
from api.app.core.config import settings
from api.app.main import app


class StubStopsGraphService:
    def get_nearest_stops(self, latitude: float, longitude: float, *, limit: int = 5):
        return [
            {
                "stop_id": "STOP_A",
                "stop_name": "Stop A",
                "stop_lat": latitude,
                "stop_lon": longitude,
                "distance_km": 0.0,
            }
        ][:limit]


class StopsApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        self.original_auth0_enabled = settings.AUTH0_ENABLED
        settings.SUPABASE_AUTH_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        settings.AUTH0_ENABLED = self.original_auth0_enabled
        app.dependency_overrides.clear()

    async def _request(self, query_string: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(f"/api/v1/stops/nearby?{query_string}")

    async def test_nearby_stops_endpoint_requires_authentication(self) -> None:
        response = await self._request("lat=28.7&lon=77.1")

        self.assertEqual(response.status_code, 401)

    async def test_nearby_stops_endpoint_returns_nearest_stops(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {"sub": "auth0|demo-user"}

        with patch(
            "api.app.api.v1.stops.get_gtfs_graph_service",
            return_value=StubStopsGraphService(),
        ):
            response = await self._request("lat=28.7&lon=77.1&limit=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["stops"]), 1)
        self.assertEqual(payload["stops"][0]["stop_id"], "STOP_A")


if __name__ == "__main__":
    unittest.main()
