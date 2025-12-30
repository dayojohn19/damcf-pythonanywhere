from django.contrib import admin

from .models import Note, Property, PropertyImage


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("text", "done", "created_at")
    list_filter = ("done",)
    search_fields = ("text",)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "price", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "address", "description")


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


PropertyAdmin.inlines = [PropertyImageInline]
