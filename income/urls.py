from django.urls import path

from . import views

urlpatterns = [
    path("", views.income_dashboard, name="income_dashboard"),
    # W2
    path("w2/add/", views.w2_add, name="w2_add"),
    path("w2/<int:pk>/edit/", views.w2_edit, name="w2_edit"),
    path("w2/<int:pk>/delete/", views.w2_delete, name="w2_delete"),
    # Bonus
    path("bonus/add/", views.bonus_add, name="bonus_add"),
    path("bonus/<int:pk>/delete/", views.bonus_delete, name="bonus_delete"),
    # Raise schedule
    path("raise/add/", views.raise_add, name="raise_add"),
    path("raise/<int:pk>/delete/", views.raise_delete, name="raise_delete"),
    # Social Security
    path("social-security/<int:person_pk>/edit/", views.ss_edit, name="ss_edit"),
    path("social-security/<int:person_pk>/delete/", views.ss_delete, name="ss_delete"),
]
