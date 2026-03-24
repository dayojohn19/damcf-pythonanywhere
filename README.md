# Reactive Django sample (HTMX) + Heroku

This is a minimal Django app with a reactive UI (HTMX) and Heroku-friendly deployment settings.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Heroku deploy (high level)

- Ensure these config vars are set:
  - `SECRET_KEY` (required)
  - `DEBUG=false`
  - `ALLOWED_HOSTS=<your-app>.herokuapp.com`
  - `CSRF_TRUSTED_ORIGINS=https://<your-app>.herokuapp.com`
  - `SECURE_SSL_REDIRECT=true`
  - Optional (Facebook auto-posting for new listings):
    - `SITE_URL=https://<your-domain>`
    - `FACEBOOK_PAGE_ID=<your page id>`
    - `FACEBOOK_PAGE_ACCESS_TOKEN=<long-lived page access token>`
- Add the Heroku Postgres addon, which provides `DATABASE_URL`.

Procfile is included:

```
web: gunicorn config.wsgi
```

Static files are served via Whitenoise.

## Heroku deploy (CLI)

Prereqs:

- Install the Heroku CLI
- You have a Heroku account and are logged in: `heroku login`

From this repo:

```bash
heroku create <your-app-name>
heroku addons:create heroku-postgresql:essential-0 -a <your-app-name>

# Required settings
heroku config:set -a <your-app-name> SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
heroku config:set -a <your-app-name> DEBUG=false
heroku config:set -a <your-app-name> ALLOWED_HOSTS=<your-app-name>.herokuapp.com
heroku config:set -a <your-app-name> CSRF_TRUSTED_ORIGINS=https://<your-app-name>.herokuapp.com
heroku config:set -a <your-app-name> SECURE_SSL_REDIRECT=true

git init
git add .
git commit -m "Initial commit"

heroku git:remote -a <your-app-name>
git push heroku main

heroku open -a <your-app-name>
```

Notes:

- Migrations run automatically on deploy because [Procfile](Procfile) includes a `release:` phase.
- Static files are collected during the Heroku build unless you set `DISABLE_COLLECTSTATIC=1`.

## Heroku deploy (GitHub)

- Push this repo to GitHub
- In the Heroku dashboard: your app → **Deploy** → connect GitHub repo → enable deploys
- Still set the same config vars listed above (Heroku dashboard → **Settings** → **Config Vars**)

---

## Database Schema

All image fields store **Cloudinary URLs** (`URLField`, max 2000 chars). String fields use `CharField` (single line) or `TextField` (multi-line).

### Note
| Field | Type | Notes |
|-------|------|-------|
| `text` | `CharField(200)` | Note content |
| `done` | `BooleanField` | Completion flag |
| `created_at` | `DateTimeField` | Auto-set on creation |

### Municipality
| Field | Type | Notes |
|-------|------|-------|
| `name` | `CharField(120)` | Unique municipality name |
| `description` | `TextField` | Optional long description |
| `properties` | `ManyToManyField → Property` | Extra associated properties |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `updated_at` | `DateTimeField` | Auto-updated on save |

### Service
| Field | Type | Notes |
|-------|------|-------|
| `name` | `CharField(120)` | Unique service name |
| `description` | `TextField` | Optional long description |
| `image` | `URLField(2000)` | **Image URL** (Cloudinary) |
| `active` | `BooleanField` | Visibility flag |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `updated_at` | `DateTimeField` | Auto-updated on save |

### ServiceImage
| Field | Type | Notes |
|-------|------|-------|
| `service` | `ForeignKey → Service` | Parent service |
| `image` | `URLField(2000)` | **Image URL** (Cloudinary) |
| `created_at` | `DateTimeField` | Auto-set on creation |

### Property
| Field | Type | Notes |
|-------|------|-------|
| `title` | `CharField(120)` | Listing title |
| `municipality` | `ForeignKey → Municipality` | Nullable location |
| `created_by` | `ForeignKey → User` | Nullable author |
| `address` | `CharField(255)` | Street address |
| `price` | `DecimalField(12,2)` | Nullable asking price |
| `status` | `CharField(20)` | `for_sale` / `for_lease` / `for_rent` / `sold` |
| `description` | `TextField` | Optional long description |
| `is_featured` | `BooleanField` | Featured listing flag |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `updated_at` | `DateTimeField` | Auto-updated on save |

### PropertyImage
| Field | Type | Notes |
|-------|------|-------|
| `property` | `ForeignKey → Property` | Parent listing |
| `image` | `URLField(2000)` | **Image URL** (Cloudinary) |
| `created_at` | `DateTimeField` | Auto-set on creation |

### ContactMessage
| Field | Type | Notes |
|-------|------|-------|
| `name` | `CharField(120)` | Sender name |
| `email` | `EmailField` | Sender email |
| `message` | `TextField` | Message body |
| `created_at` | `DateTimeField` | Auto-set on creation |

### BookingRequest
| Field | Type | Notes |
|-------|------|-------|
| `property` | `ForeignKey → Property` | Target listing |
| `name` | `CharField(120)` | Requester name |
| `email` | `EmailField` | Requester email |
| `requested_date` | `DateField` | Preferred viewing date |
| `message` | `TextField` | Optional notes |
| `created_at` | `DateTimeField` | Auto-set on creation |

### Agent
| Field | Type | Notes |
|-------|------|-------|
| `user` | `OneToOneField → User` | Nullable linked user account |
| `name` | `CharField(120)` | Display name |
| `title` | `CharField(120)` | Job title |
| `email` | `EmailField` | Contact email |
| `phone` | `CharField(50)` | Contact phone |
| `photo` | `URLField(2000)` | **Image URL** (Cloudinary) |
| `bio` | `TextField` | Optional biography |
| `active` | `BooleanField` | Visibility flag |
| `properties` | `ManyToManyField → Property` | Assigned listings |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `updated_at` | `DateTimeField` | Auto-updated on save |
