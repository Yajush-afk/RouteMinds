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

    def test_auth0_domain_and_issuer_are_normalized(self) -> None:
        settings = Settings(
            _env_file=None,
            AUTH0_DOMAIN="https://tenant.auth0.com/",
            AUTH0_ISSUER="https://tenant.auth0.com",
        )

        self.assertEqual(settings.AUTH0_DOMAIN, "tenant.auth0.com")
        self.assertEqual(settings.AUTH0_ISSUER, "https://tenant.auth0.com/")

    def test_auth0_algorithms_are_normalized(self) -> None:
        settings = Settings(
            _env_file=None,
            AUTH0_ALGORITHMS=" rs256, es256 ",
        )

        self.assertEqual(settings.AUTH0_ALGORITHMS, "RS256,ES256")

    def test_runtime_validation_requires_auth0_settings_when_enabled(self) -> None:
        settings = Settings(
            _env_file=None,
            AUTH0_ENABLED=True,
            AUTH0_DOMAIN="",
            AUTH0_AUDIENCE="",
            AUTH0_REALTIME_REQUIRED_PERMISSION="",
        )

        with self.assertRaises(ValueError) as context:
            settings.validate_runtime_configuration()

        self.assertIn("AUTH0_DOMAIN", str(context.exception))
        self.assertIn("AUTH0_AUDIENCE", str(context.exception))
        self.assertIn("AUTH0_REALTIME_REQUIRED_PERMISSION", str(context.exception))

    def test_runtime_validation_rejects_mismatched_issuer_host(self) -> None:
        settings = Settings(
            _env_file=None,
            AUTH0_ENABLED=True,
            AUTH0_DOMAIN="tenant.auth0.com",
            AUTH0_AUDIENCE="https://route-minds-api",
            AUTH0_ISSUER="https://other-tenant.auth0.com/",
            AUTH0_REALTIME_REQUIRED_PERMISSION="realtime:manage",
        )

        with self.assertRaises(ValueError) as context:
            settings.validate_runtime_configuration()

        self.assertIn("AUTH0_ISSUER host must match AUTH0_DOMAIN", str(context.exception))

    def test_runtime_validation_accepts_complete_auth0_configuration(self) -> None:
        settings = Settings(
            _env_file=None,
            AUTH0_ENABLED=True,
            AUTH0_DOMAIN="tenant.auth0.com",
            AUTH0_AUDIENCE="https://route-minds-api",
            AUTH0_ISSUER="https://tenant.auth0.com/",
            AUTH0_REALTIME_REQUIRED_PERMISSION="realtime:manage",
        )

        settings.validate_runtime_configuration()


if __name__ == "__main__":
    unittest.main()
