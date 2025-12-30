from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Note


def index(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.all()
    return render(request, "core/index.html", {"notes": notes})


@require_POST
def note_create(request: HttpRequest) -> HttpResponse:
    text = (request.POST.get("text") or "").strip()
    if text:
        Note.objects.create(text=text)

    if request.headers.get("HX-Request") == "true":
        return _notes_list_partial(request)
    return redirect("index")


@require_POST
def note_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Note, pk=pk)
    note.done = not note.done
    note.save(update_fields=["done"])

    if request.headers.get("HX-Request") == "true":
        return _note_row_partial(request, note)
    return redirect("index")


@require_POST
def note_delete(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Note, pk=pk)
    note.delete()

    if request.headers.get("HX-Request") == "true":
        return _notes_list_partial(request)
    return redirect("index")


def _notes_list_partial(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.all()
    return render(request, "core/_notes_list.html", {"notes": notes})


def _note_row_partial(request: HttpRequest, note: Note) -> HttpResponse:
    return render(request, "core/_note_row.html", {"note": note})
