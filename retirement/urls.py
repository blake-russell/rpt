from django.urls import path

from . import views

urlpatterns = [
    path("", views.retirement_dashboard, name="retirement_dashboard"),
]
