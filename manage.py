#!/usr/bin/env python
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def main() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if load_dotenv is not None:
        load_dotenv()
    elif env_path.exists():
        print(
            "Warning: .env exists but python-dotenv is not available in this interpreter. "
            "Run the server with your venv Python (e.g. .venv/bin/python manage.py runserver) or install python-dotenv.",
            file=sys.stderr,
        )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? "
            "Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
