from django.contrib import admin

from .models import RetirementSettings


@admin.register(RetirementSettings)
class RetirementSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "target_retirement_year",
        "target_life_expectancy_year",
        "annual_spending_today",
        "portfolio_growth_rate_pct",
    )
