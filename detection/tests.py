from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from brands.models import Brand
from monitoring.models import MonitoredItem
from services.groq_service import GroqServiceError
from .models import RiskFinding
from .risk_scoring import score_item


class RiskScoringTests(TestCase):
    def test_unofficial_domain_and_suspicious_language_raise_risk(self):
        user = get_user_model().objects.create_user(username="analyst", password="long-password-123")
        brand = Brand.objects.create(owner=user, name="Example Bank", official_domains=["example.com"])
        item = MonitoredItem.objects.create(
            brand=brand,
            source="social",
            name="Example Bank Support",
            url="https://fake.example.net/login",
            content="Verify your account urgently",
        )
        result = score_item(item, brand)
        self.assertGreaterEqual(result["risk_score"], 55)
        self.assertIn(result["severity"], ("high", "critical"))

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="scan-analyst", password="long-password-123"
        )
        self.brand = Brand.objects.create(
            owner=self.user, name="Example Bank", official_domains=["example.com"]
        )
        self.item = MonitoredItem.objects.create(
            brand=self.brand,
            source="social",
            name="Example Bank Support",
            url="https://fake.example.net/login",
            content="Verify your account urgently",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @override_settings(GROQ_API_KEY="")
    def test_scan_succeeds_with_clear_status_when_ai_is_not_configured(self):
        response = self.client.post(
            "/detection/api/findings/scan/",
            {"item_id": self.item.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ai_status"], RiskFinding.AIStatus.NOT_CONFIGURED)
        self.assertIn("GROQ_API_KEY", response.data["ai_error"])
        self.assertGreaterEqual(response.data["risk_score"], 55)

    @override_settings(GROQ_API_KEY="test-key")
    @patch("detection.services.analyze_threat")
    def test_scan_excludes_official_domains_from_ai_analysis(self, analyze_threat_mock):
        self.item.url = "https://login.example.com/account"
        self.item.save(update_fields=["url"])
        response = self.client.post(
            "/detection/api/findings/scan/",
            {"item_id": self.item.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ai_status"], RiskFinding.AIStatus.SKIPPED)
        self.assertEqual(response.data["risk_score"], 0)
        analyze_threat_mock.assert_not_called()

    @override_settings(GROQ_API_KEY="test-key")
    @patch("detection.services.analyze_threat")
    def test_scan_stores_ai_summary_and_recommendation(self, analyze_threat_mock):
        analyze_threat_mock.return_value = {
            "summary": "The profile uses a lookalike domain and requests verification.",
            "recommendation": "Verify the account through the official website.",
        }
        response = self.client.post(
            "/detection/api/findings/scan/",
            {"item_id": self.item.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ai_status"], RiskFinding.AIStatus.COMPLETED)
        self.assertEqual(
            response.data["ai_recommendation"],
            "Verify the account through the official website.",
        )
        finding = RiskFinding.objects.get(pk=response.data["id"])
        self.assertGreaterEqual(finding.risk_score, 55)
        analyze_threat_mock.assert_called_once()

    @override_settings(GROQ_API_KEY="test-key")
    @patch(
        "detection.services.analyze_threat",
        side_effect=GroqServiceError("Groq returned HTTP 503."),
    )
    def test_ai_failure_is_reported_without_losing_rule_based_scan(self, analyze_threat_mock):
        response = self.client.post(
            "/detection/api/findings/scan/",
            {"item_id": self.item.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ai_status"], RiskFinding.AIStatus.FAILED)
        self.assertEqual(response.data["ai_error"], "Groq returned HTTP 503.")
        self.assertGreaterEqual(response.data["risk_score"], 55)
