from django.urls import path

from . import views

urlpatterns = [
    path("", views.properties_index, name="properties_index"),
    path("properties/create/", views.property_create, name="property_create"),
    path("properties/<int:pk>/edit/", views.property_edit, name="property_edit"),
    path("properties/<int:pk>/delete/", views.property_delete, name="property_delete"),
    path("property-images/<int:pk>/delete/", views.property_image_delete, name="property_image_delete"),

    # Keep the original demo routes available
    path("notes/", views.notes_index, name="notes_index"),
    path("notes/create/", views.note_create, name="note_create"),
    path("notes/<int:pk>/toggle/", views.note_toggle, name="note_toggle"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
]
