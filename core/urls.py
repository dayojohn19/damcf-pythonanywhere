from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("services/", views.services, name="services"),
    path("services/create/", views.service_create, name="service_create"),
    path("services/<int:pk>/edit/", views.service_edit, name="service_edit"),
    path("services/<int:pk>/delete/", views.service_delete, name="service_delete"),
    path("listings/", views.listings, name="listings"),
    path("listings/<int:pk>/", views.property_detail, name="property_detail"),
    path("listings/<int:pk>/book/", views.property_book, name="property_book"),
    path("listings/<int:pk>/featured/", views.property_set_featured, name="property_set_featured"),
    path("agents/", views.agents, name="agents"),
    path("municipalities/", views.municipalities, name="municipalities"),
    path("contact/", views.contact, name="contact"),

    # CRUD endpoints
    path("listings/create/", views.property_create, name="property_create"),
    path("listings/<int:pk>/edit/", views.property_edit, name="property_edit"),
    path("listings/<int:pk>/delete/", views.property_delete, name="property_delete"),
    path("property-images/<int:pk>/delete/", views.property_image_delete, name="property_image_delete"),

    # Agents management
    path("agents/create/", views.agent_create, name="agent_create"),
    path("agents/<int:pk>/edit/", views.agent_edit, name="agent_edit"),
    path("agents/<int:pk>/delete/", views.agent_delete, name="agent_delete"),

    # Municipality management
    path("municipalities/create/", views.municipality_create, name="municipality_create"),
    path("municipalities/<int:pk>/edit/", views.municipality_edit, name="municipality_edit"),
    path("municipalities/<int:pk>/delete/", views.municipality_delete, name="municipality_delete"),

    # Keep the original demo routes available
    path("notes/", views.notes_index, name="notes_index"),
    path("notes/create/", views.note_create, name="note_create"),
    path("notes/<int:pk>/toggle/", views.note_toggle, name="note_toggle"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
]
