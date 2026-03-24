import os
from pathlib import Path
import sys

try:
	from dotenv import load_dotenv
except Exception:
	load_dotenv = None

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if load_dotenv is not None:
	load_dotenv()
else:
	env_path = Path(__file__).resolve().parent.parent / ".env"
	if env_path.exists():
		print(
			"Warning: .env exists but python-dotenv is not available. SMTP env vars may not load.",
			file=sys.stderr,
		)

application = get_asgi_application()
