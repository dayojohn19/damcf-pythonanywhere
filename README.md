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
