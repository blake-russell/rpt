from django.contrib import admin

from .models import AppSettings


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "api_provider", "openrouter_default_model", "updated_at"]
