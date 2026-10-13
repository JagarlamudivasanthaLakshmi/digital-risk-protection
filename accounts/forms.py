from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class RegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = (
            "Choose any username. Spaces and symbols are allowed (up to 150 characters)."
        )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")
