from __future__ import annotations

from pathlib import Path
import os
from urllib.parse import unquote, urlparse

import dj_database_url
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
try:
    import certifi
except Exception:
    certifi = None
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    # PythonAnywhere commonly uses a custom WSGI file, so load .env from settings.
    load_dotenv(BASE_DIR / ".env")


def _env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_list(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


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

_on_heroku = bool(os.environ.get("DYNO"))

# Default to DEBUG=False on Heroku (DYNO env var is set).
DEBUG = _env_bool(os.environ.get("DEBUG"), default=not bool(os.environ.get("DYNO")))
# DEBUG = False  # Force DEBUG=False for production safety; override with env var if needed.
# Heroku-friendly host/origin configuration.
# Recommended in Heroku:
#   heroku config:set ALLOWED_HOSTS=your-app.herokuapp.com,your-custom-domain.com
#   heroku config:set CSRF_TRUSTED_ORIGINS=https://your-app.herokuapp.com,https://your-custom-domain.com
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    if os.environ.get("DYNO") and not DEBUG:
        # Allow the Heroku app domain (still recommend setting ALLOWED_HOSTS explicitly).
        ALLOWED_HOSTS = [".herokuapp.com"]
    else:
        ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Always allow the live custom domain and its www variant.
_default_public_hosts = [
    "damcfrealty-and-businessconsultancy.com",
    "www.damcfrealty-and-businessconsultancy.com",
]
for _host in _default_public_hosts:
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

_site_url = (os.environ.get("SITE_URL") or "").strip().rstrip("/")
if _site_url:
    try:
        parsed = urlparse(_site_url)
        if parsed.hostname:
            if parsed.hostname not in ALLOWED_HOSTS and (".herokuapp.com" not in ALLOWED_HOSTS):
                ALLOWED_HOSTS.append(parsed.hostname)
    except Exception:
        pass

if _on_heroku:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
for _host in _default_public_hosts:
    _origin = f"https://{_host}"
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)
if _site_url:
    try:
        parsed = urlparse(_site_url)
        if parsed.scheme and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)
    except Exception:
        pass

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "core.apps.CoreConfig",
]

def _cloudinary_credentials_from_env() -> dict[str, str]:
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    # Also support the common single-variable format:
    # CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>
    if not (cloud_name and api_key and api_secret):
        cloudinary_url = os.environ.get("CLOUDINARY_URL", "").strip()
        if cloudinary_url:
            parsed = urlparse(cloudinary_url)
            if parsed.scheme == "cloudinary":
                cloud_name = cloud_name or (parsed.hostname or "")
                api_key = api_key or unquote(parsed.username or "")
                api_secret = api_secret or unquote(parsed.password or "")

    return {
        "CLOUD_NAME": cloud_name,
        "API_KEY": api_key,
        "API_SECRET": api_secret,
    }


_cloudinary_storage = _cloudinary_credentials_from_env()
_has_cloudinary_credentials = all(_cloudinary_storage.values())

# Cloudinary-first media uploads unless explicitly disabled.
_use_cloudinary = _env_bool(os.environ.get("USE_CLOUDINARY"), default=True)
if _use_cloudinary:
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
    if _has_cloudinary_credentials:
        CLOUDINARY_STORAGE = _cloudinary_storage

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",  # GZip compression for better performance
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

HARDCODED_DATABASE_URL = "postgres://u2vbp82enb8hvq:pc7ed6f8928c2036089905b5dd57430e156b97c380fa04742401526a4c523ead5@carsriardc474g.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d3r12vci6039ds"

DATABASES = {
    "default": dj_database_url.parse(
        HARDCODED_DATABASE_URL,
        conn_max_age=600,
        ssl_require=_on_heroku,
    )
}

# sqlite3 backend does not support sslmode; remove it if present.
if DATABASES["default"].get("ENGINE", "").endswith("sqlite3"):
    db_options = DATABASES["default"].get("OPTIONS") or {}
    if isinstance(db_options, dict):
        db_options.pop("sslmode", None)
        if db_options:
            DATABASES["default"]["OPTIONS"] = db_options
        else:
            DATABASES["default"].pop("OPTIONS", None)

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if _on_heroku:
    # Use manifest storage on Heroku (collectstatic runs during build).
    _staticfiles_storage_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage"
else:
    # Locally (DEBUG or not), skip the manifest to avoid needing collectstatic.
    _staticfiles_storage_backend = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Optional: phone number (E.164 digits) for WhatsApp booking requests.
# Example: 14155552671 (no '+' and no spaces). If empty, WhatsApp redirect is disabled.
WHATSAPP_BOOKING_PHONE = os.environ.get("WHATSAPP_BOOKING_PHONE", "").strip()

if _use_cloudinary and _has_cloudinary_credentials:
    _default_storage_backend = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    _default_storage_backend = "django.core.files.storage.FileSystemStorage"

# Django 4.2+ / 5+ / 6+ storage configuration.
STORAGES = {
    "default": {
        "BACKEND": _default_storage_backend,
    },
    "staticfiles": {
        "BACKEND": _staticfiles_storage_backend,
    },
}

# Backward compatibility for older integrations that still read these settings.
DEFAULT_FILE_STORAGE = _default_storage_backend
STATICFILES_STORAGE = _staticfiles_storage_backend

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Optional: if set, new agent accounts created from /agents/ will use this password.
# If unset/empty, a random temporary password is generated and shown to the superuser.
AGENT_DEFAULT_PASSWORD = os.environ.get("AGENT_DEFAULT_PASSWORD", "")

# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool(os.environ.get("SECURE_SSL_REDIRECT"), default=_on_heroku)
SESSION_COOKIE_SECURE = _env_bool(os.environ.get("SESSION_COOKIE_SECURE"), default=_on_heroku)
CSRF_COOKIE_SECURE = _env_bool(os.environ.get("CSRF_COOKIE_SECURE"), default=_on_heroku)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds

# Performance & Security optimizations
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000" if _on_heroku else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS"), default=_on_heroku)
SECURE_HSTS_PRELOAD = _env_bool(os.environ.get("SECURE_HSTS_PRELOAD"), default=_on_heroku)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Database connection pooling (already configured with conn_max_age)
# Cache configuration for performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}
 
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
    # On some macOS Python installs, system cert trust is incomplete.
    # Point Django SMTP to a known CA bundle to avoid TLS verify failures.
    EMAIL_SSL_CERTFILE = os.environ.get("EMAIL_SSL_CERTFILE", "").strip()
    if not EMAIL_SSL_CERTFILE and certifi is not None:
        EMAIL_SSL_CERTFILE = certifi.where()
else:
    # Dev-friendly fallback: prints email to the console.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
