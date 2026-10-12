from django.db import models
from django.db.models import Q

from brands.models import Brand


SOCIAL_SOURCE_VALUES = (
    "social",
    "instagram",
    "facebook",
    "x",
    "linkedin",
    "youtube",
    "tiktok",
)


class MonitoredItem(models.Model):
    class Source(models.TextChoices):
        SOCIAL = "social", "Social media"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        X = "x", "X (Twitter)"
        LINKEDIN = "linkedin", "LinkedIn"
        YOUTUBE = "youtube", "YouTube"
        TIKTOK = "tiktok", "TikTok"
        APP_STORE = "app_store", "App store"
        GOOGLE_PLAY = "google_play", "Google Play"
        WEB = "web", "Web"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="monitored_items")
    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=1000, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-last_seen_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("brand", "source", "external_id"),
                condition=~Q(external_id=""),
                name="unique_external_monitored_item",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_source_display()})"
