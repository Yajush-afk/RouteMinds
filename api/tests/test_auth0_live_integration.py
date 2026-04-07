from __future__ import annotations

import os
import unittest

import httpx


LIVE_BASE_URL = os.environ.get("ROUTEMINDS_SUPABASE_TEST_BASE_URL", "").strip()
LIVE_ACCESS_TOKEN = os.environ.get("ROUTEMINDS_SUPABASE_TEST_ACCESS_TOKEN", "").strip()
LIVE_REALTIME_TOKEN = os.environ.get("ROUTEMINDS_SUPABASE_TEST_REALTIME_TOKEN", "").strip()
LIVE_INVALID_TOKEN = os.environ.get("ROUTEMINDS_SUPABASE_TEST_INVALID_TOKEN", "").strip()


@unittest.skipUnless(
    LIVE_BASE_URL and LIVE_ACCESS_TOKEN,
    "Set ROUTEMINDS_SUPABASE_TEST_BASE_URL and ROUTEMINDS_SUPABASE_TEST_ACCESS_TOKEN to run live Supabase verification.",
)
class LiveSupabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def _request(self, method: str, path: str, token: str | None = None) -> httpx.Response:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(base_url=LIVE_BASE_URL, timeout=30.0) as client:
            return await client.request(method, path, headers=headers)

    async def test_auth_me_rejects_missing_token(self) -> None:
        response = await self._request("GET", "/auth/me")

        self.assertEqual(response.status_code, 401)

    async def test_auth_me_accepts_valid_access_token(self) -> None:
        response = await self._request("GET", "/auth/me", LIVE_ACCESS_TOKEN)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["subject"])
        self.assertIn("claims", payload)

    @unittest.skipUnless(
        LIVE_INVALID_TOKEN,
        "Set ROUTEMINDS_SUPABASE_TEST_INVALID_TOKEN to verify invalid-token rejection.",
    )
    async def test_auth_me_rejects_invalid_access_token(self) -> None:
        response = await self._request("GET", "/auth/me", LIVE_INVALID_TOKEN)

        self.assertEqual(response.status_code, 401)

    @unittest.skipUnless(
        LIVE_REALTIME_TOKEN,
        "Set ROUTEMINDS_SUPABASE_TEST_REALTIME_TOKEN to verify realtime authorization.",
    )
    async def test_realtime_status_accepts_permissioned_token(self) -> None:
        response = await self._request("GET", "/realtime/status", LIVE_REALTIME_TOKEN)

        self.assertEqual(response.status_code, 200)
        self.assertIn("configured", response.json())


if __name__ == "__main__":
    unittest.main()
