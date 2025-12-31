from django import template
from django.core.files.storage import default_storage

register = template.Library()

try:
    from cloudinary.utils import cloudinary_url
    _has_cloudinary = True
except Exception:
    cloudinary_url = None
    _has_cloudinary = False

@register.filter(name="cloud_url")
def cloud_url(file_field, width=0):
    """Return a Cloudinary URL for the given FileField or file name.

    Usage in templates:
      {% load cloudinary_extras %}
      <img src="{{ img.image|cloud_url:300 }}" />

    Falls back to the storage `url()` for non-Cloudinary setups.
    """
    if not file_field:
        return ""

    # Accept either FieldFile or string
    public_id = None
    try:
        # FieldFile has .name
        public_id = getattr(file_field, "name", None) or str(file_field)
    except Exception:
        public_id = str(file_field)

    if not public_id:
        return ""

    # If cloudinary is available and configured, build a transformed URL
    if _has_cloudinary:
        try:
            opts = {}
            if width:
                opts["width"] = int(width)
                opts["crop"] = "fill"
            url, _ = cloudinary_url(public_id, **opts)
            return url
        except Exception:
            # Fall back to storage URL on any error
            return default_storage.url(public_id)

    # No cloudinary: return storage URL
    return default_storage.url(public_id)
