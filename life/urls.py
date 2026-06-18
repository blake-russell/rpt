from django.urls import path

from . import views

urlpatterns = [
    path("", views.life_dashboard, name="life_dashboard"),
    path("event/add/", views.life_event_add, name="life_event_add"),
    path("event/<int:pk>/edit/", views.life_event_edit, name="life_event_edit"),
    path("event/<int:pk>/delete/", views.life_event_delete, name="life_event_delete"),
]
