from .settings import *

# Override DB for one-off export/import into SQLite.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "database.sqlite3",
    }
}
