from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from io import StringIO
from rest_framework.test import APIClient
from unittest.mock import patch

from brands.models import Brand
from detection.models import RiskFinding
from alerts.models import Alert
from .collectors.providers import CollectorError
from .models import MonitoredItem
from .services import scan_brand


class MonitoringAPITests(TestCase):
    def test_cannot_create_item_for_another_users_brand(self):
        owner = get_user_model().objects.create_user(username="owner", password="long-password-123")
        other = get_user_model().objects.create_user(username="other", password="long-password-123")
        brand = Brand.objects.create(owner=owner, name="Protected Brand")
        client = APIClient()
        client.force_authenticate(other)
        response = client.post(
            "/monitoring/api/items/",
            {"brand": brand.pk, "source": "social", "name": "Impersonator"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MonitoredItem.objects.count(), 0)

    def test_scan_api_requires_authentication(self):
        response = APIClient().post(
            "/monitoring/api/scan/",
            {"brand": 1, "source": "social"},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_scan_api_rejects_a_brand_owned_by_another_user(self):
        owner = get_user_model().objects.create_user(
            username="scan-owner", password="long-password-123"
        )
        other = get_user_model().objects.create_user(
            username="scan-other", password="long-password-123"
        )
        brand = Brand.objects.create(owner=owner, name="Private Brand")
        client = APIClient()
        client.force_authenticate(other)

        response = client.post(
            "/monitoring/api/scan/",
            {"brand": brand.pk, "source": "social"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(MonitoredItem.objects.count(), 0)


class MonitoringWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="monitoring-user", password="long-password-123"
        )
        self.brand = Brand.objects.create(
            owner=self.user,
            name="Northstar Bank",
            official_domains=["northstar.example"],
            official_social_accounts=["https://bsky.app/profile/northstar.example"],
        )

    @patch("monitoring.management.commands.scan_brands.scan_brand")
    def test_scheduled_scan_command_runs_enabled_sources(self, scan_mock):
        scan_mock.return_value = {
            "found": 2,
            "new": 1,
            "updated": 1,
            "alerts": 1,
            "warnings": [],
        }
        output = StringIO()

        call_command(
            "scan_brands",
            brand_id=self.brand.pk,
            limit=10,
            stdout=output,
        )

        self.assertEqual(scan_mock.call_count, 3)
        self.assertIn("Completed 3 scan(s).", output.getvalue())
        self.assertEqual(
            {call.args[1] for call in scan_mock.call_args_list},
            {"social", "app_store", "google_play"},
        )

    @patch("monitoring.management.commands.scan_brands.scan_brand")
    def test_scheduled_scan_command_reports_provider_failures(self, scan_mock):
        scan_mock.side_effect = CollectorError("Provider unavailable.")
        output = StringIO()
        errors = StringIO()

        with self.assertRaisesRegex(CommandError, "3 scan\\(s\\) failed"):
            call_command(
                "scan_brands",
                brand_id=self.brand.pk,
                stdout=output,
                stderr=errors,
            )

        self.assertIn("social", errors.getvalue())
        self.assertIn("Provider unavailable.", errors.getvalue())
        self.assertIn("Completed 0 scan(s).", output.getvalue())

    def test_scheduled_scan_command_validates_limit(self):
        with self.assertRaisesRegex(CommandError, "--limit must be between 1 and 50"):
            call_command("scan_brands", brand_id=self.brand.pk, limit=51)

    @override_settings(GROQ_API_KEY="")
    @patch("monitoring.services.collect_social_mentions")
    def test_scan_imports_scores_and_alerts_candidate_and_deduplicates(self, collect):
        collect.return_value = (
            [{
                "source": "social",
                "external_id": "bluesky:did:plc:fake",
                "name": "Northstar Bank Support",
                "url": "https://bsky.app/profile/northstar-help.bsky.social",
                "publisher": "Bluesky",
                "content": "Verify your account urgently",
                "metadata": {"provider": "bluesky"},
            }],
            [],
        )

        result = scan_brand(self.brand, "social")
        again = scan_brand(self.brand, "social")

        self.assertEqual(result["new"], 1)
        self.assertEqual(result["alerts"], 1)
        self.assertEqual(again["new"], 0)
        self.assertEqual(again["updated"], 1)
        self.assertEqual(MonitoredItem.objects.count(), 1)
        self.assertEqual(RiskFinding.objects.count(), 1)
        self.assertEqual(Alert.objects.count(), 1)

    @override_settings(GROQ_API_KEY="")
    @patch(
        "monitoring.services.collect_social_mentions",
        side_effect=CollectorError("Bluesky and Mastodon are unavailable."),
    )
    def test_scan_surfaces_provider_outage(self, collect):
        with self.assertRaisesRegex(CollectorError, "unavailable"):
            scan_brand(self.brand, "social")

    @override_settings(GROQ_API_KEY="")
    @patch("monitoring.services.collect_social_mentions")
    def test_scan_does_not_import_official_accounts(self, collect):
        collect.return_value = (
            [{
                "source": "social",
                "external_id": "bluesky:did:plc:official",
                "name": "Northstar Bank",
                "url": "https://bsky.app/profile/northstar.example",
                "publisher": "Bluesky",
                "content": "Official",
                "metadata": {"provider": "bluesky"},
            }],
            [],
        )

        result = scan_brand(self.brand, "social")

        self.assertEqual(result["new"], 0)
        self.assertEqual(MonitoredItem.objects.count(), 0)
        self.assertEqual(RiskFinding.objects.count(), 0)
        self.assertEqual(Alert.objects.count(), 0)

    @override_settings(GROQ_API_KEY="")
    @patch("monitoring.services.collect_google_play_listings", return_value=([], []))
    def test_google_play_page_scan_redirects_without_server_error(self, collect):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("monitoring-scan"),
            {"brand": self.brand.pk, "source": "google_play"},
        )

        self.assertRedirects(response, reverse("app-monitoring"))
        collect.assert_called_once()

    def test_app_monitoring_page_exposes_both_store_choices(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("app-monitoring"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="app_store"')
        self.assertContains(response, 'value="google_play"')

    def test_social_page_exposes_manual_platform_choices(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("social-monitoring"))

        self.assertEqual(response.status_code, 200)
        for platform in ("instagram", "facebook", "x", "linkedin", "youtube", "tiktok"):
            with self.subTest(platform=platform):
                self.assertContains(response, f'value="{platform}"')

    @override_settings(GROQ_API_KEY="")
    def test_manual_social_platform_candidate_is_stored_and_scored(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("monitoring-item-create"),
            {
                "brand": self.brand.pk,
                "source": "instagram",
                "name": "Northstar Bank Support",
                "url": "https://www.instagram.com/northstar-support",
                "publisher": "Unknown",
                "content": "Verify your account now",
            },
        )

        self.assertRedirects(response, reverse("social-monitoring"))
        item = MonitoredItem.objects.get()
        self.assertEqual(item.source, "instagram")
        self.assertGreaterEqual(item.findings.get().risk_score, 50)

    def test_manual_social_entry_rejects_a_registered_official_account(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("monitoring-item-create"),
            {
                "brand": self.brand.pk,
                "source": "instagram",
                "name": "Official Northstar",
                "url": "https://bsky.app/profile/northstar.example",
            },
        )

        self.assertRedirects(response, reverse("social-monitoring"))
        self.assertFalse(MonitoredItem.objects.exists())

    @override_settings(GROQ_API_KEY="")
    @patch("monitoring.services.collect_social_mentions")
    def test_scan_ignores_malformed_legacy_official_domains(self, collect):
        self.brand.official_domains = ["[][]google.com", "northstar.example"]
        self.brand.save(update_fields=["official_domains"])
        collect.return_value = (
            [{
                "source": "social",
                "external_id": "bluesky:did:plc:lookalike",
                "name": "Northstar Bank Support",
                "url": "https://northstar-help.example/profile",
                "publisher": "Bluesky",
                "content": "Verify your account.",
                "metadata": {"provider": "bluesky"},
            }],
            [],
        )

        result = scan_brand(self.brand, "social")

        self.assertEqual(result["scored"], 1)

    @override_settings(GROQ_API_KEY="")
    @patch("monitoring.services.collect_google_play_listings")
    def test_google_play_scan_imports_and_scores_candidates(self, collect):
        self.brand.official_apps = ["com.northstar.official"]
        self.brand.save(update_fields=["official_apps"])
        collect.return_value = (
            [{
                "source": "google_play",
                "external_id": "google_play:net.imposter.app",
                "name": "Northstar Bank Support",
                "url": "https://play.google.com/store/apps/details?id=net.imposter.app",
                "publisher": "Unknown Publisher",
                "content": "Verify your account now",
                "metadata": {
                    "provider": "google_play",
                    "bundle_id": "net.imposter.app",
                    "store_id": "net.imposter.app",
                    "artwork": "",
                },
            }],
            [],
        )

        result = scan_brand(self.brand, "google_play")

        self.assertEqual(result["new"], 1)
        self.assertEqual(result["scored"], 1)
        self.assertEqual(MonitoredItem.objects.get().source, "google_play")
        self.assertEqual(RiskFinding.objects.count(), 1)
        collect.assert_called_once()

    @patch("monitoring.services.collect_google_play_listings")
    def test_google_play_scan_rejects_when_disabled_for_brand(self, collect):
        self.brand.google_play_search_enabled = False
        self.brand.save(update_fields=["google_play_search_enabled"])

        with self.assertRaisesRegex(CollectorError, "disabled"):
            scan_brand(self.brand, "google_play")

        collect.assert_not_called()
