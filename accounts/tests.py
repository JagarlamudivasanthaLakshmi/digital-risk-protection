from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def test_registration_page_is_available(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_uses_project_template(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WELCOME BACK")

    def test_registration_creates_configured_user_and_logs_them_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-analyst",
                "email": "analyst@example.com",
                "password1": "R4ndom-Secure-Pass-2026!",
                "password2": "R4ndom-Secure-Pass-2026!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = get_user_model().objects.get(username="new-analyst")
        self.assertEqual(user.email, "analyst@example.com")
        self.assertTrue(user.is_authenticated)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
