from django.db import models

from brands.models import Brand
from monitoring.models import MonitoredItem


class RiskFinding(models.Model):
    class AIStatus(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "Not configured"
        SKIPPED = "skipped", "Skipped"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="findings")
    monitored_item = models.ForeignKey(
        MonitoredItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="findings"
    )
    risk_score = models.PositiveSmallIntegerField(default=0)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    signals = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    ai_status = models.CharField(
        max_length=20, choices=AIStatus.choices, default=AIStatus.NOT_CONFIGURED
    )
    ai_summary = models.TextField(blank=True)
    ai_recommendation = models.TextField(blank=True)
    ai_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.brand}: {self.severity} ({self.risk_score})"
