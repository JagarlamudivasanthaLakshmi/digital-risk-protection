from django import forms

from brands.models import Brand


MANUAL_SOCIAL_SOURCES = (
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("x", "X (Twitter)"),
    ("linkedin", "LinkedIn"),
    ("youtube", "YouTube"),
    ("tiktok", "TikTok"),
)


class MonitoringScanForm(forms.Form):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.none(),
        empty_label="Choose a brand",
        widget=forms.Select(attrs={"class": "monitoring-select"}),
    )
    source = forms.ChoiceField(
        choices=(
            ("social", "Social profiles (Bluesky + Mastodon)"),
            ("app_store", "Apple App Store"),
            ("google_play", "Google Play"),
        ),
        widget=forms.HiddenInput(),
    )

    def __init__(self, user, *args, source=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = Brand.objects.filter(owner=user)
        if source in ("app_store", "google_play"):
            self.fields["source"].widget = forms.Select(attrs={"class": "monitoring-select"})
            self.fields["source"].choices = (
                ("app_store", "Apple App Store"),
                ("google_play", "Google Play"),
            )
            self.initial["source"] = source
        elif source == "social":
            self.fields["source"].choices = (("social", "Social profiles (Bluesky + Mastodon)"),)
            self.initial["source"] = source

    def clean_source(self):
        source = self.cleaned_data["source"]
        if source not in ("social", "app_store", "google_play"):
            raise forms.ValidationError("Choose a supported monitoring source.")
        return source


class ManualMonitoredItemForm(forms.Form):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.none(),
        empty_label="Choose a brand",
    )
    name = forms.CharField(max_length=255)
    url = forms.URLField(max_length=1000, required=False)
    publisher = forms.CharField(max_length=255, required=False)
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    source = forms.ChoiceField(
        choices=(
            ("social", "Social media"),
            ("app_store", "Apple App Store"),
            ("google_play", "Google Play"),
        ),
        widget=forms.HiddenInput(),
    )

    def __init__(self, user, *args, source=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = Brand.objects.filter(owner=user)
        if source == "social" or source in dict(MANUAL_SOCIAL_SOURCES):
            self.fields["source"].widget = forms.Select()
            self.fields["source"].choices = MANUAL_SOCIAL_SOURCES
            self.fields["source"].initial = "instagram"
            self.initial["source"] = (
                source if source in dict(MANUAL_SOCIAL_SOURCES) else "instagram"
            )
        elif source in ("app_store", "google_play"):
            self.fields["source"].widget = forms.Select()
            self.fields["source"].choices = (
                ("app_store", "Apple App Store"),
                ("google_play", "Google Play"),
            )
            self.initial["source"] = source
        elif source == "social":
            self.fields["source"].choices = (("social", "Social media"),)
            self.initial["source"] = source

    def clean_source(self):
        source = self.cleaned_data["source"]
        if source not in (
            "social",
            *(value for value, _ in MANUAL_SOCIAL_SOURCES),
            "app_store",
            "google_play",
        ):
            raise forms.ValidationError("Choose a supported monitoring source.")
        return source
