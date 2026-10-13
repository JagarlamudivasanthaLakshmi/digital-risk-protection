from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from brands.models import Brand
from monitoring.models import MonitoredItem
from .services import dashboard_stats


class DashboardTests(TestCase):
    def test_dashboard_links_resolve_to_html_pages(self):
        self.assertEqual(reverse("brand-list"), "/brands/")
        self.assertEqual(reverse("alert-list"), "/alerts/")

    def test_stats_only_include_the_current_users_brands(self):
        user = get_user_model().objects.create_user(username="analyst", password="long-password-123")
        other = get_user_model().objects.create_user(username="other", password="long-password-123")
        Brand.objects.create(owner=user, name="My Brand")
        Brand.objects.create(owner=other, name="Other Brand")
        self.assertEqual(dashboard_stats(user)["brand_count"], 1)

    def test_dashboard_search_finds_owned_monitored_items(self):
        user = get_user_model().objects.create_user(username="searcher", password="long-password-123")
        brand = Brand.objects.create(owner=user, name="Example Brand")
        MonitoredItem.objects.create(
            brand=brand,
            source="social",
            name="Example Support",
            url="https://social.example.net/profile",
        )
        self.client.force_login(user)
        response = self.client.get("/dashboard/", {"q": "social.example.net"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Example Support")

    def test_dashboard_renders_reference_sections_and_account_menu(self):
        user = get_user_model().objects.create_user(username="dashboard-layout-user")
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Risk Trends (Last 7 Days)")
        self.assertContains(response, "Risk Level Distribution")
        self.assertContains(response, "Recent Detections")
        self.assertContains(response, "Top Threats")
        self.assertContains(response, 'class="user-menu"')
        self.assertContains(response, "Log out")
