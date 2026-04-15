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

    def search_stops(self, query: str, *, limit: int = 8):
        return [
            {
                "stop_id": "STOP_A",
                "stop_name": f"{query.title()} Terminal",
                "stop_lat": 28.7,
                "stop_lon": 77.1,
                "match_score": 80.0,
            },
            {
                "stop_id": "STOP_B",
                "stop_name": f"{query.title()} Depot",
                "stop_lat": 28.71,
                "stop_lon": 77.11,
                "match_score": 60.0,
            },
        ][:limit]


class StopsApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        settings.SUPABASE_AUTH_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        app.dependency_overrides.clear()

    async def _request(self, path: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    async def test_nearby_stops_endpoint_requires_authentication(self) -> None:
        response = await self._request("/api/v1/stops/nearby?lat=28.7&lon=77.1")

        self.assertEqual(response.status_code, 401)

    async def test_unversioned_nearby_stops_alias_requires_authentication(self) -> None:
        response = await self._request("/stops/nearby?lat=28.7&lon=77.1")

        self.assertEqual(response.status_code, 401)

    async def test_stop_search_endpoint_is_public(self) -> None:
        response = await self._request("/api/v1/stops/search?q=narela")

        self.assertEqual(response.status_code, 200)

    async def test_nearby_stops_endpoint_returns_nearest_stops(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
        }

        with patch(
            "api.app.api.v1.stops.get_gtfs_graph_service",
            return_value=StubStopsGraphService(),
        ):
            response = await self._request("/api/v1/stops/nearby?lat=28.7&lon=77.1&limit=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["stops"]), 1)
        self.assertEqual(payload["stops"][0]["stop_id"], "STOP_A")

    async def test_stop_search_endpoint_returns_ranked_results(self) -> None:
        with patch(
            "api.app.api.v1.stops.get_gtfs_graph_service",
            return_value=StubStopsGraphService(),
        ):
            response = await self._request("/api/v1/stops/search?q=narela&limit=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["stops"]), 2)
        self.assertEqual(payload["stops"][0]["stop_id"], "STOP_A")
        self.assertGreater(payload["stops"][0]["match_score"], payload["stops"][1]["match_score"])

    async def test_unversioned_stop_search_alias_is_public(self) -> None:
        with patch(
            "api.app.api.v1.stops.get_gtfs_graph_service",
            return_value=StubStopsGraphService(),
        ):
            response = await self._request("/stops/search?q=narela&limit=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["stops"]), 2)


if __name__ == "__main__":
    unittest.main()
