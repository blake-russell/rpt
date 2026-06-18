from django.contrib import admin

from .models import DebtInfo, Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("description", "loan_type", "current_balance", "monthly_payment", "is_active")
    list_filter = ("loan_type", "is_active")
    search_fields = ("description",)


@admin.register(DebtInfo)
class DebtInfoAdmin(admin.ModelAdmin):
    list_display = (
        "homeowners_insurance_yearly",
        "real_estate_tax_yearly",
        "car_insurance_total_premium",
        "car_insurance_frequency",
    )
