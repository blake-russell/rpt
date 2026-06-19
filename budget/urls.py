from django.urls import path

from . import views

urlpatterns = [
    path("", views.budget_dashboard, name="budget_dashboard"),
    path("import/", views.import_csv, name="budget_import_csv"),
    path(
        "transactions/bulk-action/",
        views.transactions_bulk_action,
        name="budget_transactions_bulk_action",
    ),
    path("transaction/<int:pk>/edit/", views.transaction_edit, name="budget_transaction_edit"),
    path(
        "transaction/<int:pk>/delete/", views.transaction_delete, name="budget_transaction_delete"
    ),
    path(
        "transaction/<int:pk>/exclude/",
        views.transaction_exclude,
        name="budget_transaction_exclude",
    ),
    path(
        "transaction/<int:pk>/include/",
        views.transaction_include,
        name="budget_transaction_include",
    ),
    path("duplicates/bulk/", views.duplicates_bulk_action, name="budget_duplicates_bulk_action"),
    path(
        "transaction/<int:pk>/duplicate-approve/",
        views.duplicate_approve,
        name="budget_duplicate_approve",
    ),
    path(
        "transaction/<int:pk>/duplicate-deny/", views.duplicate_deny, name="budget_duplicate_deny"
    ),
    path("mapping/save/", views.save_mapping, name="budget_save_mapping"),
    path("mapping/bulk/", views.bulk_save_mappings, name="budget_bulk_save_mappings"),
    path("categories/", views.categories_manage, name="budget_categories"),
    path("categories/<int:pk>/edit/", views.category_edit, name="budget_category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="budget_category_delete"),
    path("exclusions/", views.exclusion_rules_manage, name="budget_exclusion_rules"),
    path("exclusions/apply/", views.apply_exclusion_rules, name="budget_apply_exclusions"),
    path("exclusions/<int:pk>/edit/", views.exclusion_rule_edit, name="budget_exclusion_rule_edit"),
    path(
        "exclusions/<int:pk>/delete/",
        views.exclusion_rule_delete,
        name="budget_exclusion_rule_delete",
    ),
]
