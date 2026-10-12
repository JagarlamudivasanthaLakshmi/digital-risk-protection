from django.contrib.auth import get_user_model
from django.test import TestCase

from brands.models import Brand
from monitoring.models import MonitoredItem
from detection.risk_scoring import score_item


class RiskScoringTests(TestCase):
    def test_allowlisted_domain_is_scored_as_zero(self):
        user = get_user_model().objects.create_user(username="risk", password="long-password-123")
        brand = Brand.objects.create(owner=user, name="Example", official_domains=["example.com"])
        item = MonitoredItem.objects.create(
            brand=brand, source="social", name="Example", url="https://login.example.com"
        )
        self.assertEqual(score_item(item, brand)["risk_score"], 0)
