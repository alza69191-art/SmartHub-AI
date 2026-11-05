import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from main import require_admin


class AdminAllowlistTests(unittest.TestCase):
    def test_allowlisted_admin_keeps_privileged_access(self):
        user = {"role": "admin", "email": "owner@example.com"}
        with patch.dict(os.environ, {"ADMIN_EMAILS": "owner@example.com"}):
            self.assertEqual(require_admin(user), user)

    def test_removed_admin_email_loses_privileged_access(self):
        user = {"role": "admin", "email": "former-admin@example.com"}
        with patch.dict(os.environ, {"ADMIN_EMAILS": "owner@example.com"}):
            with self.assertRaises(HTTPException) as raised:
                require_admin(user)
        self.assertEqual(raised.exception.status_code, 403)

    def test_regular_user_never_gets_privileged_access(self):
        user = {"role": "user", "email": "owner@example.com"}
        with patch.dict(os.environ, {"ADMIN_EMAILS": "owner@example.com"}):
            with self.assertRaises(HTTPException) as raised:
                require_admin(user)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
