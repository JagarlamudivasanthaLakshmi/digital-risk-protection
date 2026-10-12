from django import forms
from django.forms import ModelForm

from .models import Alert


class AlertUpdateForm(ModelForm):
    class Meta:
        model = Alert
        fields = ("status", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
