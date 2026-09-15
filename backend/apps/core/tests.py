from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

GOOGLE_SETTINGS = override_settings(
    GOOGLE_CLIENT_ID="test-client-id",
    ALLOWED_EMAIL_DOMAIN="burntstack.com",
    ADMIN_EMAILS=["admin@burntstack.com"],
)


def fake_payload(**overrides):
    payload = {
        "email": "jane@burntstack.com",
        "email_verified": True,
        "hd": "burntstack.com",
        "given_name": "Jane",
        "family_name": "Doe",
    }
    payload.update(overrides)
    return payload


@GOOGLE_SETTINGS
class GoogleLoginTests(APITestCase):
    def setUp(self):
        self.url = reverse("google_login")
        cache.clear()  # each test gets a fresh login-throttle window

    def test_missing_credential_is_rejected(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_rejects_everything_when_not_configured(self):
        response = self.client.post(self.url, {"credential": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("apps.core.views.verify_google_token")
    def test_invalid_token_is_rejected(self, mock_verify):
        mock_verify.side_effect = ValueError("bad token")
        response = self.client.post(self.url, {"credential": "bad"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.core.views.verify_google_token")
    def test_valid_domain_email_creates_user_and_returns_tokens(self, mock_verify):
        mock_verify.return_value = fake_payload()
        response = self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        user = User.objects.get(username="jane@burntstack.com")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.email, "jane@burntstack.com")
        self.assertFalse(user.is_staff)

    @patch("apps.core.views.verify_google_token")
    def test_wrong_hosted_domain_is_rejected(self, mock_verify):
        mock_verify.return_value = fake_payload(email="jane@gmail.com", hd="")
        response = self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(username="jane@gmail.com").exists())

    @patch("apps.core.views.verify_google_token")
    def test_spoofed_email_suffix_with_wrong_hd_is_rejected(self, mock_verify):
        # hd is the authoritative claim — an email that merely *looks* right
        # with a mismatched (or absent) hd must still be rejected.
        mock_verify.return_value = fake_payload(hd="not-burntstack.com")
        response = self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.core.views.verify_google_token")
    def test_unverified_email_is_rejected(self, mock_verify):
        mock_verify.return_value = fake_payload(email_verified=False)
        response = self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.core.views.verify_google_token")
    def test_admin_email_gets_is_staff(self, mock_verify):
        mock_verify.return_value = fake_payload(email="admin@burntstack.com")
        self.client.post(self.url, {"credential": "good"}, format="json")
        user = User.objects.get(username="admin@burntstack.com")
        self.assertTrue(user.is_staff)

    @patch("apps.core.views.verify_google_token")
    def test_second_login_reuses_the_same_user(self, mock_verify):
        mock_verify.return_value = fake_payload()
        self.client.post(self.url, {"credential": "good"}, format="json")
        self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertEqual(User.objects.filter(username="jane@burntstack.com").count(), 1)

    @patch("apps.core.views.verify_google_token")
    def test_is_staff_is_re_synced_on_every_login(self, mock_verify):
        mock_verify.return_value = fake_payload()
        self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertFalse(User.objects.get(username="jane@burntstack.com").is_staff)

        with override_settings(ADMIN_EMAILS=["jane@burntstack.com"]):
            self.client.post(self.url, {"credential": "good"}, format="json")
        self.assertTrue(User.objects.get(username="jane@burntstack.com").is_staff)
