from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from pathlib import Path

from core.models import PropertyImage, Agent

class Command(BaseCommand):
    help = "Migrate existing local media files for PropertyImage and Agent.photo to the configured DEFAULT_FILE_STORAGE (e.g., Cloudinary)."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        self.stdout.write(f"Using MEDIA_ROOT={media_root}")

        # Process PropertyImage
        self.stdout.write("Processing PropertyImage objects...")
        count = 0
        for img in PropertyImage.objects.all():
            field = img.image
            if not field:
                continue
            name = field.name
            # Skip if the name looks like an external URL
            if name.startswith("http://") or name.startswith("https://"):
                continue

            local_path = media_root / name
            if not local_path.exists():
                self.stdout.write(self.style.WARNING(f"File not found for PropertyImage id={img.pk}: {local_path}"))
                continue

            # Re-open and save to default storage (this will upload to Cloudinary when configured)
            with local_path.open("rb") as f:
                django_file = File(f)
                # preserve the original filename under the storage
                new_name = name
                field.save(new_name, django_file, save=False)
                img.save(update_fields=["image"])  # ensure model updated
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded PropertyImage id={img.pk} -> {field.name}"))

        self.stdout.write(self.style.SUCCESS(f"PropertyImage files re-uploaded: {count}"))

        # Process Agent photos
        self.stdout.write("Processing Agent photos...")
        count = 0
        for agent in Agent.objects.exclude(photo__exact=""):
            field = agent.photo
            if not field:
                continue
            name = field.name
            if name.startswith("http://") or name.startswith("https://"):
                continue

            local_path = media_root / name
            if not local_path.exists():
                self.stdout.write(self.style.WARNING(f"File not found for Agent id={agent.pk}: {local_path}"))
                continue

            with local_path.open("rb") as f:
                django_file = File(f)
                new_name = name
                field.save(new_name, django_file, save=False)
                agent.save(update_fields=["photo"])
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded Agent id={agent.pk} -> {field.name}"))

        self.stdout.write(self.style.SUCCESS(f"Agent photos re-uploaded: {count}"))
