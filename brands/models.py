from django.conf import settings
from django.db import models


class Brand(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brands")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    official_domains = models.JSONField(default=list, blank=True)
    official_publishers = models.JSONField(default=list, blank=True)
    official_social_accounts = models.JSONField(default=list, blank=True)
    official_apps = models.JSONField(default=list, blank=True)
    social_search_enabled = models.BooleanField(default=True)
    app_store_search_enabled = models.BooleanField(default=True)
    google_play_search_enabled = models.BooleanField(default=True)
    logo = models.ImageField(upload_to="brand_logos/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        unique_together = (("owner", "name"),)

    def __str__(self):
        return self.name
