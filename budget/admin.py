from django.contrib import admin

from .models import ExclusionRule, ExpenseCategory, MerchantMapping, Transaction


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color_hex", "is_debt_service")
    search_fields = ("name",)


@admin.register(MerchantMapping)
class MerchantMappingAdmin(admin.ModelAdmin):
    list_display = ("raw_description", "friendly_name", "category")
    list_filter = ("category",)
    search_fields = ("raw_description", "friendly_name")


@admin.register(ExclusionRule)
class ExclusionRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "description_contains", "source", "is_active")
    list_filter = ("source", "is_active")
    search_fields = ("name", "description_contains", "note")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "raw_description",
        "friendly_name",
        "amount",
        "category",
        "source",
        "status",
        "is_excluded",
    )
    list_filter = ("source", "category", "status", "date", "is_excluded")
    search_fields = ("raw_description", "friendly_name", "check_number", "import_hash")
    date_hierarchy = "date"
