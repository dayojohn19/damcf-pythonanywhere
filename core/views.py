from decimal import Decimal, InvalidOperation
import secrets

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib import messages
from django.urls import reverse

from .models import Agent, ContactMessage, Municipality, Note, Property, PropertyImage, Service
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

try:
    import cloudinary.uploader as _cloudinary_uploader
    # Only enable Cloudinary usage when credentials are configured in settings
    creds = getattr(settings, "CLOUDINARY_STORAGE", {}) or {}
    _HAS_CLOUDINARY = bool(creds.get("API_KEY") and creds.get("API_SECRET") and creds.get("CLOUD_NAME"))
except Exception:
    _cloudinary_uploader = None
    _HAS_CLOUDINARY = False


def _upload_file_and_get_url(file_obj, folder: str) -> str | None:
    """Try to upload `file_obj` to Cloudinary and return URL, else save to MEDIA and return URL."""
    if file_obj is None:
        return None
    # Try Cloudinary first
    if _HAS_CLOUDINARY and _cloudinary_uploader is not None:
        try:
            result = _cloudinary_uploader.upload(file_obj, folder=f"realestate/{folder}")
            secure = result.get("secure_url") or result.get("url")
            if secure:
                return secure
        except Exception as e:
            print('Cant Save in Cloudinary')
            print(e)
            pass
    # try:

    #     # Fallback: use Django `default_storage` so this works with local MEDIA_ROOT
    #     # or remote storage backends (S3, etc.). Return the public URL if available.
    #     try:
    #         name = secrets.token_urlsafe(8) + "-" + getattr(file_obj, "name", "upload")
    #         storage_path = f"{folder}/{name}"
    #         # read file content (works for InMemoryUploadedFile and TemporaryUploadedFile)
    #         content = ContentFile(file_obj.read())
    #         saved_path = default_storage.save(storage_path, content)
    #         try:
    #             return default_storage.url(saved_path)
    #         except Exception:
    #             # If storage doesn't provide a URL, try MEDIA_URL fallback
    #             media_url = (settings.MEDIA_URL or "/media").rstrip("/")
    #             return f"{media_url}/{saved_path.lstrip('/')}"
    #     except Exception:
    #         # final fallback: give up and return None
    #         return None
    # except Exception:
    #     return None


def _is_superuser(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def _is_agent(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name="Agents").exists()


def _can_create_listing(user) -> bool:
    return _is_superuser(user) or _is_agent(user)


def _selected_municipality_id(request: HttpRequest) -> int | None:
    raw = (request.GET.get("municipality") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def index(request: HttpRequest) -> HttpResponse:
    return home(request)


def home(request: HttpRequest) -> HttpResponse:
    featured = Property.objects.select_related("municipality").prefetch_related("images").all()[:6]
    return render(request, "core/home.html", {"featured": featured})


def services(request: HttpRequest) -> HttpResponse:
    qs = Service.objects.all()
    if not (request.user.is_authenticated and request.user.is_superuser):
        qs = qs.filter(active=True)
    return render(request, "core/services.html", {"services": qs})


def notes_index(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.all()
    return render(request, "core/notes.html", {"notes": notes})


def listings(request: HttpRequest) -> HttpResponse:
    page_number = request.GET.get("page") or 1

    selected_municipality_id = _selected_municipality_id(request)
    qs = Property.objects.select_related("municipality").prefetch_related("images").all()
    if selected_municipality_id is not None:
        qs = qs.filter(municipality_id=selected_municipality_id)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "can_create_listing": _can_create_listing(request.user),
        "municipalities": Municipality.objects.order_by("name"),
        "selected_municipality_id": selected_municipality_id,
    }

    # HTMX pagination/filtering swaps only the listings list.
    # But boosted navigation (full page transitions) must return full HTML.
    hx_request = (request.headers.get("HX-Request") or "").lower() == "true"
    hx_boosted = (request.headers.get("HX-Boosted") or "").lower() == "true"
    if hx_request and not hx_boosted:
        return render(request, "core/_properties_list.html", context)

    return render(request, "core/listings.html", context)


def property_detail(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(
        Property.objects.select_related("municipality", "created_by").prefetch_related(
            "images",
            "created_by__agent_profile",
        ),
        pk=pk,
    )
    agent = getattr(prop.created_by, "agent_profile", None)
    agent_properties = None
    if agent:
        agent_properties = agent.properties.select_related("municipality").prefetch_related("images").all().exclude(pk=prop.pk)
    return render(
        request,
        "core/property_detail.html",
        {
            "property": prop,
            "agent": agent,
            "agent_properties": agent_properties,
        },
    )


def contact(request: HttpRequest) -> HttpResponse:
    service = (request.GET.get("service") or "").strip()
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        message = (request.POST.get("message") or "").strip()

        if name and email and message:
            ContactMessage.objects.create(name=name, email=email, message=message)
            return render(request, "core/contact.html", {"success": True})

        return render(
            request,
            "core/contact.html",
            {
                "success": False,
                "error": "Please fill out name, email, and message.",
                "name": name,
                "email": email,
                "message": message,
                "service": service,
            },
        )

    prefill_message = ""
    if service:
        prefill_message = f"Booking request: {service}\n\n"

    return render(request, "core/contact.html", {"message": prefill_message, "service": service})


@require_http_methods(["GET", "POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        auth_logout(request)
        return redirect("home")
    return render(request, "registration/logout_confirm.html")


def agents(request: HttpRequest) -> HttpResponse:
    qs = Agent.objects.all()
    if not (request.user.is_authenticated and request.user.is_superuser):
        qs = qs.filter(active=True)
    my_agent = getattr(request.user, "agent_profile", None) if request.user.is_authenticated else None
    return render(request, "core/agents.html", {"agents": qs, "my_agent": my_agent})


def municipalities(request: HttpRequest) -> HttpResponse:
    qs = Municipality.objects.order_by("name")
    return render(request, "core/municipalities.html", {"municipalities": qs})


@require_POST
@user_passes_test(_is_superuser)
def service_create(request: HttpRequest) -> HttpResponse:
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    active = (request.POST.get("active") or "") == "on"

    if name:
        Service.objects.update_or_create(
            name=name,
            defaults={"description": description, "active": active},
        )

    if request.headers.get("HX-Request") == "true":
        return _services_grid_partial(request)
    return redirect("services")


def service_edit(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk)

    if not (request.user.is_authenticated and request.user.is_superuser):
        return redirect("services")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            service.name = name
        service.description = (request.POST.get("description") or "").strip()
        service.active = (request.POST.get("active") or "") == "on"
        service.save(update_fields=["name", "description", "active"])
        return redirect("services")

    return render(request, "core/service_edit.html", {"service": service})


@require_POST
@user_passes_test(_is_superuser)
def service_delete(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk)
    service.delete()

    if request.headers.get("HX-Request") == "true":
        return _services_grid_partial(request)
    return redirect("services")


@require_POST
@user_passes_test(_is_superuser)
def municipality_create(request: HttpRequest) -> HttpResponse:
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    if name:
        Municipality.objects.update_or_create(
            name=name,
            defaults={"description": description},
        )

    if request.headers.get("HX-Request") == "true":
        return _municipalities_list_partial(request)
    return redirect("municipalities")


def municipality_edit(request: HttpRequest, pk: int) -> HttpResponse:
    municipality = get_object_or_404(Municipality, pk=pk)

    if not (request.user.is_authenticated and request.user.is_superuser):
        return redirect("municipalities")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            municipality.name = name
        municipality.description = (request.POST.get("description") or "").strip()
        municipality.save(update_fields=["name", "description"])
        return redirect("municipalities")

    return render(request, "core/municipality_edit.html", {"municipality": municipality})


@require_POST
@user_passes_test(_is_superuser)
def municipality_delete(request: HttpRequest, pk: int) -> HttpResponse:
    municipality = get_object_or_404(Municipality, pk=pk)
    municipality.delete()

    if request.headers.get("HX-Request") == "true":
        return _municipalities_list_partial(request)
    return redirect("municipalities")


@require_POST
@user_passes_test(_is_superuser)
def agent_create(request: HttpRequest) -> HttpResponse:
    name = (request.POST.get("name") or "").strip()
    title = (request.POST.get("title") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    bio = (request.POST.get("bio") or "").strip()
    active = (request.POST.get("active") or "") == "on"

    if name:
        user = None
        if email:
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "is_active": True},
            )
            temp_password = settings.AGENT_DEFAULT_PASSWORD or secrets.token_urlsafe(12)
            if created or not user.has_usable_password():
                user.set_password(temp_password)
                user.save(update_fields=["password"])
                messages.success(
                    request,
                    f"Agent account created/updated. Login: {email}  Password: {temp_password} (ask them to change it).",
                )
            else:
                messages.info(
                    request,
                    f"Agent user already exists for {email}. Password unchanged.",
                )

            agents_group, _ = Group.objects.get_or_create(name="Agents")
            user.groups.add(agents_group)
        else:
            messages.warning(request, "Agent created without email; no login account was created.")


        photo_url = None
        photo_file = request.FILES.get("photo")
        if photo_file is not None:
            photo_url = _upload_file_and_get_url(photo_file, "agents")

        Agent.objects.create(
            user=user,
            name=name,
            title=title,
            email=email,
            phone=phone,
            bio=bio,
            active=active,
            photo=photo_url,
        )

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse("")
        response.headers["HX-Redirect"] = reverse("agents")
        return response
    return redirect("agents")


def agent_edit(request: HttpRequest, pk: int) -> HttpResponse:
    agent = get_object_or_404(Agent, pk=pk)
    print('Agent')

    is_superuser = request.user.is_authenticated and request.user.is_superuser
    print('is SuperUser')
    is_self = request.user.is_authenticated and agent.user_id == request.user.id
    if not (is_superuser or is_self):
        return redirect("agents")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            agent.name = name

        agent.title = (request.POST.get("title") or "").strip()
        agent.phone = (request.POST.get("phone") or "").strip()
        agent.bio = (request.POST.get("bio") or "").strip()

        # Only superusers can change login/email linkage and active status.
        if is_superuser:
            new_email = (request.POST.get("email") or "").strip()
            agent.email = new_email
            agent.active = (request.POST.get("active") or "") == "on"
        else:
            # For self-edit, keep the email and active values unchanged.
            new_email = agent.email

        if request.FILES.get("photo"):
            photo_file = request.FILES.get("photo")
            photo_url = _upload_file_and_get_url(photo_file, "agents")
            if photo_url:
                agent.photo = photo_url

        if is_superuser and new_email:
            User = get_user_model()
            if agent.user is None:
                user, created = User.objects.get_or_create(
                    username=new_email,
                    defaults={"email": new_email, "is_active": True},
                )
                if created:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                agent.user = user

            if agent.user is not None:
                if not agent.user.email:
                    agent.user.email = new_email
                    agent.user.save(update_fields=["email"])
                agents_group, _ = Group.objects.get_or_create(name="Agents")
                agent.user.groups.add(agents_group)

        agent.save()
        return redirect("agents")

    return render(request, "core/agent_edit.html", {"agent": agent})


@require_POST
@user_passes_test(_is_superuser)
def agent_delete(request: HttpRequest, pk: int) -> HttpResponse:
    agent = get_object_or_404(Agent, pk=pk)
    agent.delete()

    if request.headers.get("HX-Request") == "true":
        return _agents_list_partial(request)
    return redirect("agents")


@require_POST
@user_passes_test(_can_create_listing)
def property_create(request: HttpRequest) -> HttpResponse:
    title = (request.POST.get("title") or "").strip()
    address = (request.POST.get("address") or "").strip()
    description = (request.POST.get("description") or "").strip()
    status = (request.POST.get("status") or "").strip() or Property.Status.FOR_SALE

    municipality = None
    municipality_raw = (request.POST.get("municipality") or "").strip()
    if municipality_raw:
        try:
            municipality_id = int(municipality_raw)
            municipality = Municipality.objects.filter(pk=municipality_id).first()
        except (TypeError, ValueError):
            municipality = None

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
            created_by=request.user if request.user.is_authenticated else None,
            municipality=municipality,
            address=address,
            description=description,
            status=status,
            price=price,
        )

        # Optional: keep the many-to-many association in sync with the primary FK.
        if municipality is not None:
            municipality.properties.add(prop)

        if _is_agent(request.user):
            agent_profile = getattr(request.user, "agent_profile", None)
            if agent_profile is not None:
                agent_profile.properties.add(prop)

        for uploaded in request.FILES.getlist("images"):
            url = _upload_file_and_get_url(uploaded, "properties")
            if url:
                PropertyImage.objects.create(property=prop, image=url)

    if request.headers.get("HX-Request") == "true":
        return _properties_list_partial(request)
    return redirect("listings")


def property_edit(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(
        Property.objects.select_related("municipality").prefetch_related("images"),
        pk=pk,
    )

    if not (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or (_is_agent(request.user) and prop.created_by_id == request.user.id)
        )
    ):
        return redirect("property_detail", pk=prop.pk)

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

        if "municipality" in request.POST:
            municipality_raw = (request.POST.get("municipality") or "").strip()
            if municipality_raw:
                try:
                    municipality_id = int(municipality_raw)
                    prop.municipality = Municipality.objects.filter(pk=municipality_id).first()
                except (TypeError, ValueError):
                    prop.municipality = None
            else:
                prop.municipality = None

        prop.save()

        for uploaded in request.FILES.getlist("images"):
            url = _upload_file_and_get_url(uploaded, "properties")
            if url:
                PropertyImage.objects.create(property=prop, image=url)

        if request.headers.get("HX-Request") == "true":
            prop.refresh_from_db()
            return _property_images_partial(request, prop)
        return redirect("listings")

    return render(
        request,
        "core/property_edit.html",
        {
            "property": prop,
            "status_choices": Property.Status.choices,
            "municipalities": Municipality.objects.order_by("name"),
        },
    )


@require_POST
def property_delete(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(Property, pk=pk)

    if not (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or (_is_agent(request.user) and prop.created_by_id == request.user.id)
        )
    ):
        return redirect("property_detail", pk=prop.pk)

    prop.delete()

    if request.headers.get("HX-Request") == "true":
        return _properties_list_partial(request)
    return redirect("listings")


@require_POST
def property_image_delete(request: HttpRequest, pk: int) -> HttpResponse:
    img = get_object_or_404(PropertyImage.objects.select_related("property"), pk=pk)
    prop = img.property

    if not (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or (_is_agent(request.user) and prop.created_by_id == request.user.id)
        )
    ):
        return redirect("property_edit", pk=prop.pk)

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

    selected_municipality_id = _selected_municipality_id(request)
    qs = Property.objects.select_related("municipality").prefetch_related("images").all()
    if selected_municipality_id is not None:
        qs = qs.filter(municipality_id=selected_municipality_id)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "core/_properties_list.html",
        {"page_obj": page_obj, "selected_municipality_id": selected_municipality_id},
    )


def _property_images_partial(request: HttpRequest, prop: Property) -> HttpResponse:
    return render(request, "core/_property_images.html", {"property": prop})


def _agents_list_partial(request: HttpRequest) -> HttpResponse:
    qs = Agent.objects.all()
    if not (request.user.is_authenticated and request.user.is_superuser):
        qs = qs.filter(active=True)
    return render(request, "core/_agents_list.html", {"agents": qs})


def _municipalities_list_partial(request: HttpRequest) -> HttpResponse:
    qs = Municipality.objects.order_by("name")
    return render(request, "core/_municipalities_list.html", {"municipalities": qs})


def _services_grid_partial(request: HttpRequest) -> HttpResponse:
    qs = Service.objects.all()
    if not (request.user.is_authenticated and request.user.is_superuser):
        qs = qs.filter(active=True)
    return render(request, "core/_services_grid.html", {"services": qs})
