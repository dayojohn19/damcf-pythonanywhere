from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from core.models import PropertyImage, Agent

try:
    import cloudinary.uploader as _cloudinary_uploader
except Exception:
    _cloudinary_uploader = None

class Command(BaseCommand):
    help = "Migrate existing local media files for PropertyImage and Agent.photo to the configured DEFAULT_FILE_STORAGE (e.g., Cloudinary)."

    def _cloudinary_enabled(self) -> bool:
        creds = getattr(settings, "CLOUDINARY_STORAGE", {}) or {}
        return bool(
            _cloudinary_uploader is not None
            and creds.get("CLOUD_NAME")
            and creds.get("API_KEY")
            and creds.get("API_SECRET")
        )

    def _local_path_from_value(self, value: str, media_root: Path) -> Path | None:
        """Map a stored URL/path string to a local file path under MEDIA_ROOT, if possible."""
        s = (value or "").strip()
        if not s:
            return None
        if s.startswith("http://") or s.startswith("https://") or s.startswith("//"):
            return None

        # Normalize leading slashes
        if s.startswith("/"):
            s = s.lstrip("/")

        media_url = (getattr(settings, "MEDIA_URL", "media/") or "media/").strip("/")
        # If stored as 'media/...' or '/media/...', strip that prefix.
        if s.startswith(media_url + "/"):
            s = s[len(media_url) + 1 :]

        return (media_root / s).resolve()

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"Using MEDIA_ROOT={media_root}")

        if not self._cloudinary_enabled():
            self.stdout.write(self.style.ERROR("Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET and re-run."))
            return

        # Process PropertyImage
        self.stdout.write("Processing PropertyImage objects...")
        count = 0
        for img in PropertyImage.objects.all():
            value = (img.image or "").strip()
            if not value:
                continue

            local_path = self._local_path_from_value(value, media_root)
            if local_path is None:
                continue
            if not local_path.exists():
                self.stdout.write(self.style.WARNING(f"File not found for PropertyImage id={img.pk}: {local_path}"))
                continue

            try:
                with local_path.open("rb") as f:
                    result = _cloudinary_uploader.upload(f, folder="realestate/properties")
                secure = result.get("secure_url") or result.get("url")
                if not secure:
                    raise RuntimeError("Cloudinary upload returned no URL")

                img.image = secure
                img.save(update_fields=["image"])
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded PropertyImage id={img.pk} -> {secure}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to upload PropertyImage id={img.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"PropertyImage files re-uploaded: {count}"))

        # Process Agent photos
        self.stdout.write("Processing Agent photos...")
        count = 0
        for agent in Agent.objects.exclude(photo__exact=""):
            value = (agent.photo or "").strip()
            if not value:
                continue

            local_path = self._local_path_from_value(value, media_root)
            if local_path is None:
                continue
            if not local_path.exists():
                self.stdout.write(self.style.WARNING(f"File not found for Agent id={agent.pk}: {local_path}"))
                continue

            try:
                with local_path.open("rb") as f:
                    result = _cloudinary_uploader.upload(f, folder="realestate/agents")
                secure = result.get("secure_url") or result.get("url")
                if not secure:
                    raise RuntimeError("Cloudinary upload returned no URL")

                agent.photo = secure
                agent.save(update_fields=["photo"])
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded Agent id={agent.pk} -> {secure}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to upload Agent id={agent.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Agent photos re-uploaded: {count}"))
