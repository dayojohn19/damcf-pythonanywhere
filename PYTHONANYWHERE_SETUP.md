# Deploying on PythonAnywhere (Django)

This guide is tailored for this project.

## 1) Create the web app

1. Log in to PythonAnywhere.
2. Go to **Web** -> **Add a new web app**.
3. Choose **Manual configuration** (not Flask/Django wizard).
4. Pick a Python version that matches your environment as closely as possible.

## 2) Clone project and create virtualenv

Open a **Bash console** on PythonAnywhere and run:

```bash
cd ~
git clone <your-repo-url> damc-real-estate
cd damc-real-estate
python -m venv ~/.virtualenvs/damc-real-estate
source ~/.virtualenvs/damc-real-estate/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Configure environment variables

Create a `.env` file in project root (`/home/digitallife11/damc-real-estate/.env`):

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=0
ALLOWED_HOSTS=digitallife11.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://digitallife11.pythonanywhere.com

# Recommended for HTTPS deployments
SECURE_SSL_REDIRECT=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1

# Cloudinary media uploads
USE_CLOUDINARY=1
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Optional: if using PostgreSQL instead of sqlite
# DATABASE_URL=postgres://user:password@host:5432/dbname

# Optional: SMTP for contact form
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=you@example.com
# SMTP_PASSWORD=...
# SMTP_USE_TLS=1
# CONTACT_TO_EMAIL=you@example.com
```

Notes:
- This repo now loads `.env` explicitly from project root in WSGI mode.
- If `DATABASE_URL` is not set, the app uses sqlite (`db.sqlite3`).
- Uploads use Cloudinary when `USE_CLOUDINARY=1` and Cloudinary credentials are set.
- To force local uploads, set `USE_CLOUDINARY=0`.

## 4) Run migrations and collect static

In Bash console:

```bash
cd ~/damc-real-estate
source ~/.virtualenvs/damc-real-estate/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 5) Set WSGI file in PythonAnywhere

In **Web** tab:
- Set **Virtualenv** to `~/.virtualenvs/damc-real-estate`
- Set **Source code** to `~/damc-real-estate`
- Open the WSGI config file (usually `/var/www/digitallife11_pythonanywhere_com_wsgi.py`) and use:

```python
import os
import sys

path = '/home/digitallife11/damc-real-estate'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 6) Static files mapping (Web tab)

Add static mapping:
- URL: `/static/`
- Directory: `/home/digitallife11/damc-real-estate/staticfiles`

Add media mapping for uploaded files:
- URL: `/media/`
- Directory: `/home/digitallife11/damc-real-estate/media`

## 7) Reload and verify

1. Click **Reload** on the Web tab.
2. Open `https://digitallife11.pythonanywhere.com`.
3. If there is an error, check:
   - Web app **Error log**
   - **Server log**

## 8) Update flow for future deploys

When you push changes:

```bash
cd ~/damc-real-estate
source ~/.virtualenvs/damc-real-estate/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Reload** in PythonAnywhere.
