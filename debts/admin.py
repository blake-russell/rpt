from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("description", "loan_type", "current_balance", "monthly_payment", "is_active")
    list_filter = ("loan_type", "is_active")
    search_fields = ("description",)
