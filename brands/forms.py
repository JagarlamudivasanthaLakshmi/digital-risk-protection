import json
from urllib.parse import urlsplit

from django import forms
from django.forms import ModelForm

from .models import Brand


class BrandProfileForm(ModelForm):
    ASSET_FIELDS = (
        "official_domains",
        "official_publishers",
        "official_social_accounts",
        "official_apps",
    )

    official_domains = forms.CharField(
        label="Official domains",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": '["example.com"]'}),
        help_text="JSON list or one domain per line.",
    )
    official_publishers = forms.CharField(
        label="Official app publishers",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": '["Example Inc."]'}),
        help_text="Names used by legitimate app-store publishers.",
    )
    official_social_accounts = forms.CharField(
        label="Official social account URLs",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": '["https://bsky.app/profile/example.com"]'}
        ),
        help_text="Enter full official profile URLs, one per line or as a JSON list.",
    )
    official_apps = forms.CharField(
        label="Official app identifiers or URLs",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": '["com.example.app", "https://apps.apple.com/app/id123"]',
            }
        ),
        help_text=(
            "Use an Apple App Store URL or numeric ID, or an Android app package/bundle ID."
        ),
    )

    class Meta:
        model = Brand
        fields = (
            "name",
            "description",
            "logo",
            "official_domains",
            "official_publishers",
            "official_social_accounts",
            "official_apps",
            "social_search_enabled",
            "app_store_search_enabled",
            "google_play_search_enabled",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.ASSET_FIELDS:
            value = getattr(self.instance, field_name, None) or []
            if not self.is_bound:
                self.initial[field_name] = json.dumps(value, indent=2)

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.ASSET_FIELDS:
            raw_value = cleaned_data.get(field_name, "")
            if not raw_value.strip():
                cleaned_data[field_name] = []
                continue
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                value = [line.strip() for line in raw_value.splitlines() if line.strip()]
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                self.add_error(field_name, "Enter a JSON list of non-empty text values or one value per line.")
                continue
            if field_name == "official_domains":
                for domain in value:
                    try:
                        parsed = urlsplit(
                            domain.strip()
                            if "://" in domain
                            else f"//{domain.strip()}"
                        )
                        hostname = parsed.hostname
                    except ValueError:
                        hostname = None
                    if not hostname:
                        self.add_error(
                            field_name,
                            "Each official domain must be a valid hostname or URL.",
                        )
                        break
            cleaned_data[field_name] = [item.strip() for item in value]
        return cleaned_data
