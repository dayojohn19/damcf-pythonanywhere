from decimal import Decimal, InvalidOperation
import os
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
from django.http import JsonResponse
from django.core.mail import EmailMessage
from django.db import transaction

from .models import Agent, BookingRequest, ContactMessage, Municipality, Note, Property, PropertyImage, Service, ServiceImage
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from datetime import date
from urllib.parse import quote


def _upload_file_and_get_url(file_obj, folder: str) -> str | None:
    """Save `file_obj` to local MEDIA storage and return a public URL."""
    if file_obj is None:
        return None

    try:
        original_name = getattr(file_obj, "name", "upload") or "upload"
        safe_name = f"{secrets.token_urlsafe(8)}-{original_name}"
        storage_path = f"{folder}/{safe_name}"

        content = ContentFile(file_obj.read())
        saved_path = default_storage.save(storage_path, content)

        try:
            url = default_storage.url(saved_path)
        except Exception:
            url = None

        if url:
            if url.startswith("http") or url.startswith("//") or url.startswith("/"):
                return url
            return "/" + url.lstrip("/")

        media_url = (getattr(settings, "MEDIA_URL", "/media/") or "/media/").strip()
        media_url = "/" + media_url.strip("/") + "/"
        return media_url + str(saved_path).lstrip("/")
    except Exception:
        return None


def _is_superuser(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def _is_agent(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name="Agents").exists()


def _can_create_listing(user) -> bool:
    return _is_superuser(user) or _is_agent(user)


def _send_agent_credentials_email(request: HttpRequest, *, name: str, email: str, temp_password: str) -> None:
    try:
        login_url = request.build_absolute_uri(reverse("login"))
    except Exception:
        login_url = request.build_absolute_uri("/accounts/login/")

    subject = "Your agent account is ready"
    body = "\n".join([
        f"Hi {name},",
        "",
        "Your DAMC Real Estate agent account has been created.",
        f"Login email: {email}",
        f"Temporary password: {temp_password}",
        "",
        "Please log in and change your password immediately.",
        f"Login: {login_url}",
    ])
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    if not from_email:
        from_email = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()

    EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email or None,
        to=[email],
    ).send(fail_silently=False)


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
    featured_qs = Property.objects.select_related("municipality").prefetch_related("images")
    featured = list(featured_qs.filter(is_featured=True).order_by("-updated_at", "-created_at")[:6])
    if not featured:
        featured = list(featured_qs.all()[:6])
    return render(request, "core/home.html", {"featured": featured})


def services(request: HttpRequest) -> HttpResponse:
    qs = Service.objects.prefetch_related("images").all()
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


@require_http_methods(["GET", "POST"])
def property_book(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(Property, pk=pk)

    if request.method == "GET":
        if (request.GET.get("clear") or "").strip() == "1":
            return HttpResponse("")
        return render(request, "core/_property_booking_form.html", {"property": prop})

    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    requested_date_raw = (request.POST.get("requested_date") or "").strip()
    message = (request.POST.get("message") or "").strip()

    errors: list[str] = []
    requested_date_val: date | None = None
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    if not requested_date_raw:
        errors.append("Please pick a date.")
    else:
        try:
            requested_date_val = date.fromisoformat(requested_date_raw)
        except ValueError:
            errors.append("Please pick a valid date.")

    if errors:
        return render(
            request,
            "core/_property_booking_form.html",
            {
                "property": prop,
                "errors": errors,
                "name": name,
                "email": email,
                "requested_date": requested_date_raw,
                "message": message,
            },
        )

    BookingRequest.objects.create(
        property=prop,
        name=name,
        email=email,
        requested_date=requested_date_val,  # type: ignore[arg-type]
        message=message,
    )

    send_whatsapp = (request.POST.get("send_whatsapp") or "").strip() == "1"
    whatsapp_phone = (getattr(settings, "WHATSAPP_BOOKING_PHONE", "") or "").strip()
    if send_whatsapp and whatsapp_phone:
        property_url = request.build_absolute_uri(reverse("property_detail", kwargs={"pk": prop.pk}))
        text_lines = [
            "Booking request",
            f"Property: {prop.title}",
            f"Date: {requested_date_raw}",
            f"Name: {name}",
            f"Email: {email}",
            f"Link: {property_url}",
        ]
        if message:
            text_lines.append(f"Message: {message}")

        wa_url = f"https://wa.me/{whatsapp_phone}?text={quote('\n'.join(text_lines))}"
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            response.headers["HX-Redirect"] = wa_url
            return response
        return redirect(wa_url)

    if request.headers.get("HX-Request") == "true":
        return render(request, "core/_property_booking_success.html", {"property": prop})

    messages.success(request, "Booking request sent.")
    return redirect("property_detail", pk=prop.pk)


def contact(request: HttpRequest) -> HttpResponse:
    service = (request.GET.get("service") or "").strip()
    prefill_name = (request.GET.get("name") or "").strip()
    prefill_email = (request.GET.get("email") or "").strip()
    prefill_requested_date = (request.GET.get("requested_date") or "").strip()
    prefill_user_message = (request.GET.get("message") or "").strip()
    prefill_address = (request.GET.get("address") or "").strip()
    prefill_municipality = (request.GET.get("municipality") or "").strip()
    property_id_raw = (request.GET.get("property") or "").strip()
    prop = None
    if property_id_raw:
        try:
            prop = Property.objects.filter(pk=int(property_id_raw)).first()
        except (TypeError, ValueError):
            prop = None

    def _wants_json() -> bool:
        accept = (request.headers.get("Accept") or "").lower()
        return "application/json" in accept or (request.headers.get("X-Requested-With") or "") == "fetch"

    if request.method == "POST":
        # Accept both Django field names (name/email) and EmailJS-style field names
        # (from_name/sender_contact) so JS and non-JS submits behave consistently.
        name = ((request.POST.get("name") or request.POST.get("from_name") or "").strip())
        email = ((request.POST.get("email") or request.POST.get("sender_contact") or "").strip())
        message = (request.POST.get("message") or "").strip()

        service_post = (
            (request.POST.get("service") or "").strip()
            or (request.POST.get("subject") or "").strip()
            or (request.POST.get("booking_inquiry") or "").strip()
        )
        effective_service = service_post or service
        save_only = (request.POST.get("save_only") or "").strip() == "1"

        if name and email and message:
            ContactMessage.objects.create(name=name, email=email, message=message)

            if save_only:
                if _wants_json():
                    return JsonResponse({"ok": True})
                return render(request, "core/contact.html", {"success": True})

            # Contact form uses EmailJS client-side, so always treat as save-only.
            if _wants_json():
                return JsonResponse({"ok": True})
            return render(request, "core/contact.html", {"success": True})
            subject = f"New contact message from {name}"
            if effective_service:
                subject = f"New booking/contact: {effective_service}  {name}"
            body_lines = [
                f"Name: {name}",
                f"Email: {email}",
            ]
            if effective_service:
                body_lines.append(f"Service: {effective_service}")
            body_lines.append("")
            body_lines.append(message)

            try:
                to_email = (getattr(settings, "CONTACT_TO_EMAIL", "") or "").strip()
                if not to_email:
                    to_email = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
                if not to_email:
                    to_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()

                from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip() or to_email
                if not to_email:
                    raise ValueError(
                        "Email is not configured. Set CONTACT_TO_EMAIL (and SMTP_HOST/SMTP_USER/SMTP_PASSWORD) in the environment or .env, and restart the server."
                    )

                msg = EmailMessage(
                    subject=subject,
                    body="\n".join(body_lines),
                    from_email=from_email,
                    to=[to_email],
                    reply_to=[email],
                )
                msg.send(fail_silently=False)
            except Exception as e:
                if _wants_json():
                    return JsonResponse({"ok": False, "error": f"Could not send email: {e}"}, status=500)
                return render(request, "core/contact.html", {"success": False, "error": f"Could not send email: {e}"})

            if _wants_json():
                return JsonResponse({"ok": True})
            return render(request, "core/contact.html", {"success": True})

        error_text = "Please fill out name, email, and message."
        if _wants_json():
            return JsonResponse({"ok": False, "error": error_text}, status=400)
        return render(
            request,
            "core/contact.html",
            {
                "success": False,
                "error": error_text,
                "name": name,
                "email": email,
                "message": message,
                "service": effective_service,
            },
        )

    # If a property was provided, default the "service" (subject) to the property title.
    if prop and not service:
        service = prop.title

    prefill_lines: list[str] = []
    if service:
        prefill_lines.append(f"Booking request: {service}")

    if prefill_requested_date:
        prefill_lines.append(f"Requested date: {prefill_requested_date}")

    if prop:
        if not prefill_address:
            prefill_address = (prop.address or "").strip()
        if not prefill_municipality and getattr(prop, "municipality", None):
            prefill_municipality = (prop.municipality.name or "").strip()

        try:
            prop_url = request.build_absolute_uri(reverse("property_detail", kwargs={"pk": prop.pk}))
        except Exception:
            prop_url = ""

        if prefill_address:
            prefill_lines.append(f"Property address: {prefill_address}")

        if prefill_municipality:
            prefill_lines.append(f"Municipality: {prefill_municipality}")

        if prop_url:
            prefill_lines.append(f"Property link: {prop_url}")

    if prefill_user_message:
        prefill_lines.append("")
        prefill_lines.append("Message:")
        prefill_lines.append(prefill_user_message)

    prefill_message = "\n".join(prefill_lines).strip()
    if prefill_message:
        prefill_message += "\n\n"

    return render(
        request,
        "core/contact.html",
        {
            "message": prefill_message,
            "service": service,
            "name": prefill_name,
            "email": prefill_email,
            "requested_date": prefill_requested_date,
        },
    )


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


@require_POST
def agent_signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("agents")

    name = (request.POST.get("name") or "").strip()
    title = (request.POST.get("title") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    phone = (request.POST.get("phone") or "").strip()
    bio = (request.POST.get("bio") or "").strip()

    errors: list[str] = []
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")

    User = get_user_model()
    if email and User.objects.filter(username__iexact=email).exists():
        errors.append("An account with this email already exists. Please log in instead.")

    if errors:
        for error in errors:
            messages.error(request, error)
        response = redirect("agents")
        response["Location"] += "#agent-signup"
        return response

    temp_password = settings.AGENT_DEFAULT_PASSWORD or secrets.token_urlsafe(12)

    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=temp_password)
        agents_group, _ = Group.objects.get_or_create(name="Agents")
        user.groups.add(agents_group)

        photo_url = None
        photo_file = request.FILES.get("photo")
        if photo_file is not None:
            photo_url = _upload_file_and_get_url(photo_file, "agents")
            if not photo_url:
                messages.error(request, "Profile photo could not be uploaded. You can add it later.")

        agent = Agent.objects.create(
            user=user,
            name=name,
            title=title,
            email=email,
            phone=phone,
            bio=bio,
            active=True,
            photo=photo_url,
        )

    try:
        _send_agent_credentials_email(request, name=name, email=email, temp_password=temp_password)
        messages.success(request, "Your agent account has been created. Check your email for your temporary password and change it after logging in.")
    except Exception as exc:
        messages.warning(
            request,
            f"Your agent account was created, but the email with your temporary password could not be sent: {exc}",
        )

    return redirect("login")


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
        service, created = Service.objects.get_or_create(
            name=name,
            defaults={"description": description, "active": active},
        )

        if not created:
            service.description = description
            service.active = active
            service.save(update_fields=["description", "active", "updated_at"])

        image_files = list(request.FILES.getlist("images") or [])
        legacy_image_file = request.FILES.get("image")
        if not image_files and legacy_image_file is not None:
            image_files = [legacy_image_file]

        first_uploaded_url: str | None = None
        for file_obj in image_files:
            url = _upload_file_and_get_url(file_obj, "services")
            if not url:
                continue
            ServiceImage.objects.create(service=service, image=url)
            if first_uploaded_url is None:
                first_uploaded_url = url

        # Keep Service.image populated as a fallback/primary image.
        if first_uploaded_url and not (service.image or "").strip():
            service.image = first_uploaded_url
            service.save(update_fields=["image", "updated_at"])

    if request.headers.get("HX-Request") == "true":
        return _services_grid_partial(request)
    return redirect("services")


def service_edit(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service.objects.prefetch_related("images"), pk=pk)

    if not (request.user.is_authenticated and request.user.is_superuser):
        return redirect("services")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            service.name = name
        service.description = (request.POST.get("description") or "").strip()
        service.active = (request.POST.get("active") or "") == "on"

        update_fields = ["name", "description", "active", "updated_at"]

        image_files = list(request.FILES.getlist("images") or [])
        legacy_image_file = request.FILES.get("image")
        if not image_files and legacy_image_file is not None:
            image_files = [legacy_image_file]

        first_uploaded_url: str | None = None
        for file_obj in image_files:
            url = _upload_file_and_get_url(file_obj, "services")
            if not url:
                continue
            ServiceImage.objects.create(service=service, image=url)
            if first_uploaded_url is None:
                first_uploaded_url = url

        if first_uploaded_url:
            service.image = first_uploaded_url
            update_fields.append("image")

        service.save(update_fields=update_fields)
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
                messages.warning(
                    request,
                    f"Agent account created/updated. Login: {email}  Password: {temp_password} (ask them to change it).",
                )

                # Send a welcome email to the new agent with their temporary credentials.
                print(f"[agent_create] Preparing welcome email for new agent: {email}")
                print(f"[agent_create] Email backend: {settings.EMAIL_BACKEND}")
                try:
                    _send_agent_credentials_email(request, name=name, email=email, temp_password=temp_password)
                    print(f"[agent_create] Welcome email sent successfully to {email}")
                except Exception as e:
                    print(f"[agent_create] ERROR sending welcome email: {e}")
                    messages.error(request, f"Agent account created, but invite email could not be sent: {e}")
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
            if not photo_url:
                messages.error(request, "Agent photo could not be uploaded. Please try again.")

        # Guard against duplicate agents for the same user account.
        existing_agent = Agent.objects.filter(user=user).first() if user else None
        if existing_agent:
            messages.warning(request, f"An agent profile already exists for {email}. Updating existing profile instead.")
            existing_agent.name = name
            existing_agent.title = title
            existing_agent.email = email
            existing_agent.phone = phone
            existing_agent.bio = bio
            existing_agent.active = active
            if photo_url:
                existing_agent.photo = photo_url
            existing_agent.save()
        else:
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
            else:
                messages.error(request, "Agent photo could not be uploaded. Please try again.")

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
        # Create the Property and any PropertyImage rows in a single transaction.
        # This ensures the post-save signal can run after commit and still see images.
        with transaction.atomic():
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
                elif uploaded is not None:
                    messages.error(request, "Could not upload one of the images. Please try again.")

        messages.success(request, "Listing saved. Facebook posting finished—check your Facebook Page.")

    if request.headers.get("HX-Request") == "true":
        # Force a full refresh so the user sees a clear completed state.
        resp = HttpResponse("")
        resp["HX-Refresh"] = "true"
        return resp
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
            elif uploaded is not None:
                messages.error(request, "Could not upload one of the images. Please try again.")

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
@user_passes_test(_is_superuser)
def property_set_featured(request: HttpRequest, pk: int) -> HttpResponse:
    prop = get_object_or_404(
        Property.objects.select_related("municipality"),
        pk=pk,
    )

    prop.is_featured = (request.POST.get("is_featured") or "") == "on"
    prop.save(update_fields=["is_featured", "updated_at"])

    if request.headers.get("HX-Request") == "true":
        return render(request, "core/_property_row.html", {"prop": prop})
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
    qs = Service.objects.prefetch_related("images").all()
    if not (request.user.is_authenticated and request.user.is_superuser):
        qs = qs.filter(active=True)
    return render(request, "core/_services_grid.html", {"services": qs})


def privacy_policy(request: HttpRequest) -> HttpResponse:
    """Privacy Policy page required by Facebook App."""
    return render(request, "core/privacy_policy.html")


def data_deletion(request: HttpRequest) -> HttpResponse:
    """Data Deletion Instructions page required by Facebook App."""
    return render(request, "core/data_deletion.html")


def terms_of_service(request: HttpRequest) -> HttpResponse:
    """Terms of Service page."""
    return render(request, "core/terms_of_service.html")


def robots_txt(request: HttpRequest) -> HttpResponse:
    """Generate robots.txt dynamically."""
    site_url = request.build_absolute_uri('/')
    sitemap_url = request.build_absolute_uri(reverse('django.contrib.sitemaps.views.sitemap'))
    
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/
Disallow: /media/agents/

Sitemap: {sitemap_url}
"""
    return HttpResponse(content, content_type="text/plain")
