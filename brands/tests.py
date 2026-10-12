from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .forms import BrandProfileForm
from .models import Brand
from .services import normalize_domains


class BrandAPITests(TestCase):
    def test_users_only_see_their_own_brands(self):
        first = get_user_model().objects.create_user(username="first", password="long-password-123")
        second = get_user_model().objects.create_user(username="second", password="long-password-123")
        Brand.objects.create(owner=first, name="First Brand")
        Brand.objects.create(owner=second, name="Second Brand")
        client = APIClient()
        client.force_authenticate(first)
        response = client.get("/brands/api/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["First Brand"])

    def test_brand_profiles_omit_apple_scan_button(self):
        user = get_user_model().objects.create_user(username="brand-owner", password="test-pass-123")
        Brand.objects.create(owner=user, name="Example Brand")
        self.client.force_login(user)

        response = self.client.get("/brands/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Scan Apple")
        self.assertContains(response, "Scan social")
        self.assertContains(response, "Scan Google Play")

    def test_brand_form_saves_empty_domain_lists_as_lists(self):
        user = get_user_model().objects.create_user(username="creator", password="long-password-123")
        self.client.force_login(user)
        response = self.client.post(
            "/brands/add/",
            {
                "name": "New Brand",
                "description": "",
                "official_domains": "",
                "official_publishers": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        brand = Brand.objects.get(name="New Brand")
        self.assertEqual(brand.official_domains, [])
        self.assertEqual(brand.official_publishers, [])

    def test_brand_form_accepts_line_separated_official_assets(self):
        form = BrandProfileForm(data={
            "name": "Example",
            "description": "",
            "official_domains": "example.com\nshop.example.com",
            "official_publishers": "Example, Inc.",
            "official_social_accounts": "https://bsky.app/profile/example.com",
            "official_apps": "com.example.app\nhttps://apps.apple.com/app/id123",
            "social_search_enabled": "on",
            "app_store_search_enabled": "on",
        })

        self.assertTrue(form.is_valid(), form.errors)
        brand = form.save(commit=False)
        self.assertEqual(brand.official_domains, ["example.com", "shop.example.com"])
        self.assertEqual(brand.official_apps, [
            "com.example.app",
            "https://apps.apple.com/app/id123",
        ])

    def test_brand_form_rejects_malformed_official_domain_values(self):
        form = BrandProfileForm(data={
            "name": "Example",
            "official_domains": "[][]google.com",
            "official_publishers": "",
            "official_social_accounts": "",
            "official_apps": "",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("official_domains", form.errors)

    def test_domain_normalization_ignores_malformed_existing_values(self):
        self.assertEqual(
            normalize_domains(["[][]google.com", "google.com"]),
            ["google.com"],
        )
