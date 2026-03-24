import os
from pathlib import Path
import sys

try:
	from dotenv import load_dotenv
except Exception:
	load_dotenv = None

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if load_dotenv is not None:
	# Always load environment variables from repo-root .env, regardless of cwd.
	load_dotenv(Path(__file__).resolve().parent.parent / ".env")
else:
	env_path = Path(__file__).resolve().parent.parent / ".env"
	if env_path.exists():
		print(
			"Warning: .env exists but python-dotenv is not available. SMTP env vars may not load.",
			file=sys.stderr,
		)

application = get_wsgi_application()
