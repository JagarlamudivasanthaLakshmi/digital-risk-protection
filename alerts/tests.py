from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from brands.models import Brand
from detection.models import RiskFinding
from .models import Alert


class AlertAPITests(TestCase):
    def test_alerts_are_scoped_to_the_owner(self):
        owner = get_user_model().objects.create_user(username="owner", password="long-password-123")
        other = get_user_model().objects.create_user(username="other", password="long-password-123")
        brand = Brand.objects.create(owner=owner, name="Private Brand")
        finding = RiskFinding.objects.create(brand=brand, risk_score=60, severity="high")
        Alert.objects.create(finding=finding)
        client = APIClient()
        client.force_authenticate(other)
        self.assertEqual(len(client.get("/alerts/api/").data), 0)

    def test_owner_can_update_investigation_status_and_notes(self):
        owner = get_user_model().objects.create_user(
            username="investigator", password="long-password-123"
        )
        brand = Brand.objects.create(owner=owner, name="Owned Brand")
        finding = RiskFinding.objects.create(brand=brand, risk_score=60, severity="high")
        alert = Alert.objects.create(finding=finding)
        self.client.force_login(owner)

        response = self.client.post(
            reverse("alert-update", args=[alert.pk]),
            {"status": "investigating", "notes": "Verifying with the brand owner."},
        )

        self.assertRedirects(response, reverse("alert-detail", args=[alert.pk]))
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.INVESTIGATING)
        self.assertEqual(alert.notes, "Verifying with the brand owner.")

    def test_user_cannot_update_another_users_alert(self):
        owner = get_user_model().objects.create_user(
            username="alert-owner", password="long-password-123"
        )
        other = get_user_model().objects.create_user(
            username="alert-other", password="long-password-123"
        )
        brand = Brand.objects.create(owner=owner, name="Private Alert Brand")
        finding = RiskFinding.objects.create(brand=brand, risk_score=60, severity="high")
        alert = Alert.objects.create(finding=finding)
        self.client.force_login(other)

        response = self.client.post(
            reverse("alert-update", args=[alert.pk]),
            {"status": "resolved", "notes": "Unauthorized"},
        )

        self.assertEqual(response.status_code, 404)
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.OPEN)
