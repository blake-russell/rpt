from django import forms

from .models import AppSettings


class AppSettingsForm(forms.ModelForm):
    class Meta:
        model = AppSettings
        fields = ["api_provider", "openrouter_api_key", "openrouter_default_model"]
        widgets = {
            "openrouter_api_key": forms.TextInput(attrs={"placeholder": "sk-or-..."}),
            "openrouter_default_model": forms.TextInput(
                attrs={"placeholder": "e.g. openai/gpt-4o"}
            ),
        }
