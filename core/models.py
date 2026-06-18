from django.db import models


class AppSettings(models.Model):
    """
    Singleton model. Always use AppSettings.get() to retrieve.
    Stores all user-configurable settings, API keys, and preferences.
    Never hardcode any of these values in source code.
    """

    # ── AI Insights API Configuration ─────────────────────────────────────────
    api_provider = models.CharField(
        max_length=30,
        choices=[("openrouter", "OpenRouter")],
        default="openrouter",
        help_text="AI API provider for the AI Insights module. OpenRouter is currently the only supported provider.",
    )
    openrouter_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Your OpenRouter API key (sk-or-...). Get one at openrouter.ai. Stored only in your local database.",
    )
    openrouter_default_model = models.CharField(
        max_length=255,
        blank=True,
        default="openai/gpt-4o",
        help_text="OpenRouter model identifier (e.g. openai/gpt-4o, anthropic/claude-3-5-sonnet). See openrouter.ai/models.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App Settings"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "App Settings"
