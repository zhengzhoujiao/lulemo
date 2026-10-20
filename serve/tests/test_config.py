import os
import secrets
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import Settings


class SecretKeySettingsTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_missing_secret_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None)

    def test_empty_short_and_placeholder_secrets_are_rejected(self):
        for value in ("", "short-secret", "change-me-" * 5, "replace-with-random-" * 3, "a" * 64):
            with self.subTest(length=len(value)):
                with self.assertRaises(ValidationError) as error:
                    Settings(_env_file=None, SECRET_KEY=value)
                if value:
                    self.assertNotIn(value, str(error.exception))

    def test_generated_secret_is_loaded_from_environment_and_hidden_in_repr(self):
        secret = secrets.token_urlsafe(48)
        os.environ["SECRET_KEY"] = secret
        settings = Settings(_env_file=None)
        self.assertEqual(settings.SECRET_KEY, secret)
        self.assertNotIn(secret, repr(settings))


if __name__ == "__main__":
    unittest.main()
