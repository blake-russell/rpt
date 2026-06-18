from django.urls import path

from . import views

urlpatterns = [
    path("", views.people_dashboard, name="people_dashboard"),
    path("add/", views.person_add, name="person_add"),
    path("<int:pk>/edit/", views.person_edit, name="person_edit"),
    path("<int:pk>/delete/", views.person_delete, name="person_delete"),
]
