from django.contrib import admin

from .models import Agent, BookingRequest, ContactMessage, Municipality, Note, Property, PropertyImage, Service, ServiceImage


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("text", "done", "created_at")
    list_filter = ("done",)
    search_fields = ("text",)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "municipality", "status", "price", "is_featured", "created_at")
    list_filter = ("status", "municipality", "is_featured")
    list_editable = ("is_featured",)
    search_fields = ("title", "address", "description")


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


PropertyAdmin.inlines = [PropertyImageInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email", "message")
    ordering = ("-created_at",)


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ("property", "requested_date", "name", "email", "created_at")
    list_filter = ("requested_date",)
    search_fields = ("name", "email", "message", "property__title")
    ordering = ("-created_at",)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "title", "email", "phone", "active", "user")
    list_filter = ("active",)
    search_fields = ("name", "title", "email", "phone", "bio")
    filter_horizontal = ("properties",)


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("properties",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "updated_at", "image")
    list_filter = ("active",)
    search_fields = ("name", "description")


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1


ServiceAdmin.inlines = [ServiceImageInline]
