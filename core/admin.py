from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("text", "done", "created_at")
    list_filter = ("done",)
    search_fields = ("text",)
