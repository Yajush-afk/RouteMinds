from __future__ import annotations

import unittest

from pydantic import ValidationError

from api.app.core.config import Settings


class SettingsValidationTests(unittest.TestCase):
    def test_cors_allow_origins_are_trimmed_and_normalized(self) -> None:
        settings = Settings(
            _env_file=None,
            CORS_ALLOW_ORIGINS=" http://localhost:5173/ , https://example.com ",
        )

        self.assertEqual(
            settings.CORS_ALLOW_ORIGINS,
            "http://localhost:5173,https://example.com",
        )

    def test_cors_allow_origins_reject_paths(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                CORS_ALLOW_ORIGINS="http://localhost:5173/app",
            )

    def test_supabase_url_and_issuer_are_normalized(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_URL="https://project.supabase.co/",
            SUPABASE_JWT_ISSUER="https://project.supabase.co/auth/v1/",
        )

        self.assertEqual(settings.SUPABASE_URL, "https://project.supabase.co")
        self.assertEqual(
            settings.SUPABASE_JWT_ISSUER,
            "https://project.supabase.co/auth/v1",
        )

    def test_supabase_algorithms_are_normalized(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_JWT_ALGORITHMS=" rs256, es256 ",
        )

        self.assertEqual(settings.SUPABASE_JWT_ALGORITHMS, "RS256,ES256")

    def test_supabase_algorithms_reject_shared_secret_algorithms(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                SUPABASE_JWT_ALGORITHMS="HS256",
            )

    def test_runtime_validation_requires_supabase_settings_when_enabled(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_AUTH_ENABLED=True,
            SUPABASE_URL="",
            SUPABASE_JWT_AUDIENCE="",
            SUPABASE_REALTIME_REQUIRED_PERMISSION="",
        )

        with self.assertRaises(ValueError) as context:
            settings.validate_runtime_configuration()

        self.assertIn("SUPABASE_URL", str(context.exception))
        self.assertIn("SUPABASE_JWT_AUDIENCE", str(context.exception))
        self.assertIn(
            "SUPABASE_REALTIME_REQUIRED_PERMISSION",
            str(context.exception),
        )

    def test_runtime_validation_rejects_mismatched_issuer_host(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_AUTH_ENABLED=True,
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_JWT_AUDIENCE="authenticated",
            SUPABASE_JWT_ISSUER="https://other-project.supabase.co/auth/v1",
            SUPABASE_REALTIME_REQUIRED_PERMISSION="realtime:manage",
        )

        with self.assertRaises(ValueError) as context:
            settings.validate_runtime_configuration()

        self.assertIn(
            "SUPABASE_JWT_ISSUER host must match SUPABASE_URL",
            str(context.exception),
        )

    def test_runtime_validation_accepts_complete_supabase_configuration(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_AUTH_ENABLED=True,
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_JWT_AUDIENCE="authenticated",
            SUPABASE_JWT_ISSUER="https://project.supabase.co/auth/v1",
            SUPABASE_REALTIME_REQUIRED_PERMISSION="realtime:manage",
        )

        settings.validate_runtime_configuration()


if __name__ == "__main__":
    unittest.main()
