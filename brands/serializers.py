from rest_framework import serializers

from .models import Brand


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = (
            "id", "name", "description", "official_domains", "official_publishers",
            "official_social_accounts", "official_apps", "social_search_enabled",
            "app_store_search_enabled", "google_play_search_enabled", "logo", "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_official_domains(self, value):
        return self._validate_text_list(value, "domain")

    def validate_official_publishers(self, value):
        return self._validate_text_list(value, "publisher")

    def validate_official_social_accounts(self, value):
        return self._validate_text_list(value, "social account URL")

    def validate_official_apps(self, value):
        return self._validate_text_list(value, "app identifier or URL")

    @staticmethod
    def _validate_text_list(value, label):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Enter a list of text values.")
        if any(len(item) > 1000 for item in value):
            raise serializers.ValidationError(f"Each {label} must be 1000 characters or fewer.")
        return value
