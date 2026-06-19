from django.urls import path

from . import views

urlpatterns = [
    path("", views.debts_dashboard, name="debts_dashboard"),
    path("add/", views.loan_add, name="loan_add"),
    path("<int:pk>/edit/", views.loan_edit, name="loan_edit"),
    path("<int:pk>/delete/", views.loan_delete, name="loan_delete"),
    path("<int:pk>/amortization/", views.loan_amortization, name="loan_amortization"),
]
