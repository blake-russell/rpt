from django.urls import path

from . import views

urlpatterns = [
    path("", views.ai_dashboard, name="ai_insights_dashboard"),
]
