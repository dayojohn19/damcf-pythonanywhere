from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("notes/create/", views.note_create, name="note_create"),
    path("notes/<int:pk>/toggle/", views.note_toggle, name="note_toggle"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
]
