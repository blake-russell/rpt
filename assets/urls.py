from django.urls import path

from . import views

urlpatterns = [
    path("", views.assets_dashboard, name="assets_dashboard"),
    # Account
    path("account/add/", views.account_add, name="account_add"),
    path("account/<int:pk>/edit/", views.account_edit, name="account_edit"),
    path("account/<int:pk>/delete/", views.account_delete, name="account_delete"),
    # Holdings
    path("account/<int:account_pk>/holding/add/", views.holding_add, name="holding_add"),
    path("holding/<int:pk>/edit/", views.holding_edit, name="holding_edit"),
    path("holding/<int:pk>/delete/", views.holding_delete, name="holding_delete"),
    # Contributions (now per holding)
    path(
        "holding/<int:holding_pk>/contribution/add/",
        views.contribution_add,
        name="contribution_add",
    ),
    path("contribution/<int:pk>/edit/", views.contribution_edit, name="contribution_edit"),
    path("contribution/<int:pk>/delete/", views.contribution_delete, name="contribution_delete"),
    # Price refresh
    path("refresh-prices/", views.refresh_prices, name="refresh_prices"),
]
