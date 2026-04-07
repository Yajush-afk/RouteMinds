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

    def test_runtime_validation_accepts_current_configuration(self) -> None:
        settings = Settings(
            _env_file=None,
            CORS_ALLOW_ORIGINS="http://localhost:5173",
        )

        settings.validate_runtime_configuration()


if __name__ == "__main__":
    unittest.main()
