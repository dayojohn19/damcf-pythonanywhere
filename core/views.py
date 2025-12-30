from decimal import Decimal, InvalidOperation

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import Note, Property, PropertyImage


def index(request: HttpRequest) -> HttpResponse:
    return properties_index(request)


def notes_index(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.all()
    return render(request, "core/notes.html", {"notes": notes})


def properties_index(request: HttpRequest) -> HttpResponse:
    page_number = request.GET.get("page") or 1
    qs = Property.objects.prefetch_related("images").all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "core/index.html",
        {
            "page_obj": page_obj,
        },
    )


@require_POST
def property_create(request: HttpRequest) -> HttpResponse:
    title = (request.POST.get("title") or "").strip()
    address = (request.POST.get("address") or "").strip()
    description = (request.POST.get("description") or "").strip()
    status = (request.POST.get("status") or "").strip() or Property.Status.FOR_SALE

    price_raw = (request.POST.get("price") or "").strip()
    price = None
    if price_raw:
        try:
            price = Decimal(price_raw)
        except (InvalidOperation, ValueError):
            price = None

    if title:
        prop = Property.objects.create(
            title=title,
            address=address,
            description=description,
            status=status,
            price=price,
        )

        for uploaded in request.FILES.getlist("images"):
            PropertyImage.objects.create(property=prop, image=uploaded)

    if request.headers.get("HX-Request") == "true":
        return _properties_list_partial(request)
    return redirect("properties_index")


def property_edit(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(Property.objects.prefetch_related("images"), pk=pk)

    if request.method == "POST":
        if "title" in request.POST:
            title = (request.POST.get("title") or "").strip()
            if title:
                prop.title = title

        if "address" in request.POST:
            prop.address = (request.POST.get("address") or "").strip()

        if "description" in request.POST:
            prop.description = (request.POST.get("description") or "").strip()

        if "status" in request.POST:
            status = (request.POST.get("status") or "").strip() or Property.Status.FOR_SALE
            prop.status = status

        if "price" in request.POST:
            price_raw = (request.POST.get("price") or "").strip()
            if price_raw:
                try:
                    prop.price = Decimal(price_raw)
                except (InvalidOperation, ValueError):
                    prop.price = None
            else:
                prop.price = None

        prop.save()

        for uploaded in request.FILES.getlist("images"):
            PropertyImage.objects.create(property=prop, image=uploaded)

        if request.headers.get("HX-Request") == "true":
            prop.refresh_from_db()
            return _property_images_partial(request, prop)
        return redirect("properties_index")

    return render(
        request,
        "core/property_edit.html",
        {"property": prop, "status_choices": Property.Status.choices},
    )


@require_POST
def property_delete(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(Property, pk=pk)
    prop.delete()

    if request.headers.get("HX-Request") == "true":
        return _properties_list_partial(request)
    return redirect("properties_index")


@require_POST
def property_image_delete(request: HttpRequest, pk: int) -> HttpResponse:
    img = get_object_or_404(PropertyImage.objects.select_related("property"), pk=pk)
    prop = img.property
    img.delete()

    if request.headers.get("HX-Request") == "true":
        prop.refresh_from_db()
        return _property_images_partial(request, prop)
    return redirect("property_edit", pk=prop.pk)


@require_POST
def note_create(request: HttpRequest) -> HttpResponse:
    text = (request.POST.get("text") or "").strip()
    if text:
        Note.objects.create(text=text)

    if request.headers.get("HX-Request") == "true":
        return _notes_list_partial(request)
    return redirect("notes_index")


@require_POST
def note_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Note, pk=pk)
    note.done = not note.done
    note.save(update_fields=["done"])

    if request.headers.get("HX-Request") == "true":
        return _note_row_partial(request, note)
    return redirect("notes_index")


@require_POST
def note_delete(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Note, pk=pk)
    note.delete()

    if request.headers.get("HX-Request") == "true":
        return _notes_list_partial(request)
    return redirect("notes_index")


def _notes_list_partial(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.all()
    return render(request, "core/_notes_list.html", {"notes": notes})


def _note_row_partial(request: HttpRequest, note: Note) -> HttpResponse:
    return render(request, "core/_note_row.html", {"note": note})


def _properties_list_partial(request: HttpRequest) -> HttpResponse:
    page_number = request.GET.get("page") or 1
    qs = Property.objects.prefetch_related("images").all()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(request, "core/_properties_list.html", {"page_obj": page_obj})


def _property_images_partial(request: HttpRequest, prop: Property) -> HttpResponse:
    return render(request, "core/_property_images.html", {"property": prop})
