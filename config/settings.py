from pathlib import Path
import os
from urllib.parse import urlparse

import dj_database_url
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


_secret_key_file = BASE_DIR / ".secret_key"
if _secret_key_file.exists():
    _file_secret_key = _secret_key_file.read_text().strip()
else:
    _file_secret_key = get_random_secret_key()
    try:
        _secret_key_file.write_text(_file_secret_key)
    except OSError:
        # In some deployed environments the filesystem may be read-only.
        pass

# Allow override via environment (recommended for production).
SECRET_KEY = os.environ.get("SECRET_KEY") or _file_secret_key

# Default to DEBUG=False on Heroku (DYNO env var is set).
DEBUG = _env_bool(os.environ.get("DEBUG"), default=not bool(os.environ.get("DYNO")))

ALLOWED_HOSTS = ["*"]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = [
    "https://damcfrealty-and-businessconsultancy.com",
    "http://damcfrealty-and-businessconsultancy.com",
    "https://www.damcfrealty-and-businessconsultancy.com",
    "http://www.damcfrealty-and-businessconsultancy.com",
]
# CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "cloudinary_storage",
    "cloudinary",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=not DEBUG,
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if DEBUG:
    # Avoid requiring `collectstatic` during local development.
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Optional: phone number (E.164 digits) for WhatsApp booking requests.
# Example: 14155552671 (no '+' and no spaces). If empty, WhatsApp redirect is disabled.
WHATSAPP_BOOKING_PHONE = os.environ.get("WHATSAPP_BOOKING_PHONE", "").strip()

# Cloudinary storage configuration
# Configure these via environment variables in production (do NOT commit secrets).
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    "API_KEY": os.environ.get("CLOUDINARY_API_KEY", ""),
    "API_SECRET": os.environ.get("CLOUDINARY_API_SECRET", ""),
}

# Also support the common single-var Cloudinary config:
#   CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
_cloudinary_url = (os.environ.get("CLOUDINARY_URL") or "").strip()
if _cloudinary_url and not (
    CLOUDINARY_STORAGE.get("CLOUD_NAME")
    and CLOUDINARY_STORAGE.get("API_KEY")
    and CLOUDINARY_STORAGE.get("API_SECRET")
):
    try:
        parsed = urlparse(_cloudinary_url)
        if parsed.scheme == "cloudinary" and parsed.hostname and parsed.username and parsed.password:
            CLOUDINARY_STORAGE["CLOUD_NAME"] = parsed.hostname
            CLOUDINARY_STORAGE["API_KEY"] = parsed.username
            CLOUDINARY_STORAGE["API_SECRET"] = parsed.password
    except Exception:
        pass

# Use Cloudinary for uploaded media files when credentials are provided.
# Fall back to local file storage if not configured.
if CLOUDINARY_STORAGE.get("CLOUD_NAME") and CLOUDINARY_STORAGE.get("API_KEY") and CLOUDINARY_STORAGE.get("API_SECRET"):
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Optional: if set, new agent accounts created from /agents/ will use this password.
# If unset/empty, a random temporary password is generated and shown to the superuser.
AGENT_DEFAULT_PASSWORD = os.environ.get("AGENT_DEFAULT_PASSWORD", "")

# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool(os.environ.get("SECURE_SSL_REDIRECT"), default=not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds

# Email (SMTP)
# To enable SMTP delivery, set at least:
#   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, CONTACT_TO_EMAIL
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = _env_bool(os.environ.get("SMTP_USE_TLS"), default=True)
SMTP_USE_SSL = _env_bool(os.environ.get("SMTP_USE_SSL"), default=False)

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "").strip() or SMTP_USER
CONTACT_TO_EMAIL = os.environ.get("CONTACT_TO_EMAIL", "").strip() or SMTP_USER

if SMTP_HOST and CONTACT_TO_EMAIL:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = SMTP_HOST
    EMAIL_PORT = SMTP_PORT
    EMAIL_HOST_USER = SMTP_USER
    EMAIL_HOST_PASSWORD = SMTP_PASSWORD
    EMAIL_USE_TLS = SMTP_USE_TLS
    EMAIL_USE_SSL = SMTP_USE_SSL
else:
    # Dev-friendly fallback: prints email to the console.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
