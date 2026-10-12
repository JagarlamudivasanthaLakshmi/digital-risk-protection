from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class APIAuthenticationTests(TestCase):
    def test_dashboard_api_requires_login(self):
        response = APIClient().get("/dashboard/api/stats/")
        self.assertIn(response.status_code, (401, 403))

    def test_dashboard_api_returns_account_scoped_stats(self):
        user = get_user_model().objects.create_user(username="api-user", password="long-password-123")
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/dashboard/api/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["brand_count"], 0)
