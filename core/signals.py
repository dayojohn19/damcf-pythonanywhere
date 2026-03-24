import os
import requests
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property


def _normalize_graph_version(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "v18.0"
    if raw.startswith("v"):
        return raw
    if raw[0].isdigit():
        return f"v{raw}"
    return raw


def _graph_url(path: str, *, graph_version: str) -> str:
    path = path.lstrip("/")
    return f"https://graph.facebook.com/{graph_version}/{path}"


def post_to_facebook(property_instance):
    """Post a property to Facebook Page with image, price, and description."""
    # Get Facebook credentials from environment variables
    page_access_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    
    if not page_access_token or not page_id:
        print("Facebook credentials not configured. Skipping Facebook post.")
        return False
    
    # Build the message with proper formatting
    status_display = property_instance.get_status_display()
    municipality = property_instance.municipality.name if property_instance.municipality else "Siargao"
    
    message_parts = [
        f"📋 {property_instance.title}",
        f"🏡 NEW LISTING",
        f"━━━━━━━━━━━━━━━━",
        "",
    ]
    
    # Price - prominently displayed
    if property_instance.price:
        price_formatted = f"₱{property_instance.price:,.0f}"
        message_parts.append(f"💰 PRICE: {price_formatted}")
        message_parts.append("")
    
    # Location details
    message_parts.append(f"📍 LOCATION: {municipality}")
    if property_instance.address:
        message_parts.append(f"📫 {property_instance.address}")
    message_parts.append("")
    
    # Status
    message_parts.append(f"✨ STATUS: {status_display}")
    message_parts.append("")
    
    # Description - show full description
    if property_instance.description:
        desc = property_instance.description.strip()
        # Facebook allows longer posts, so show more
        if len(desc) > 500:
            desc = desc[:497] + "..."
        message_parts.append("📝 INFORMATION:")
        message_parts.append(desc)
        message_parts.append("")
    
    # Call to action
    message_parts.append("━━━━━━━━━━━━━━━━")
    message_parts.append("💬 Contact us for viewing schedule!")
    message_parts.append("📞 +639300157769")
    message_parts.append("📧 damcfrealtyinc@gmail.com")
    message_parts.append("")
    
    # Add website link (needs absolute URL; set SITE_URL in env)
    site_url = (os.environ.get("SITE_URL") or "").strip().rstrip("/")
    if site_url:
        property_url = f"{site_url}/listings/{property_instance.id}/"
        message_parts.append(f"🔗 View full details: {property_url}")
        message_parts.append("")
    
    # Hashtags
    message_parts.append("#DAMCFRealty #RealEstate #Siargao #PropertyListing")
    if status_display == "For sale":
        message_parts.append("#PropertyForSale #HouseAndLot")
    elif status_display == "For rent":
        message_parts.append("#ForRent #RentalProperty")
    
    message = "\n".join(message_parts)
    
    graph_version = _normalize_graph_version(os.environ.get("FACEBOOK_GRAPH_VERSION") or "v18.0")

    # Get all images (oldest-first by model ordering)
    images = list(property_instance.images.all())
    
    try:
        # If there are images, create a single multi-photo feed post.
        # Flow:
        #   1) Upload each photo as unpublished (published=false)
        #   2) Create /feed post with attached_media=[{media_fbid: <id>}, ...]
        public_image_urls: list[str] = []
        for img in images:
            raw = getattr(img, "image", None)
            if not raw:
                continue
            s = str(raw).strip()
            if s.startswith(("http://", "https://")):
                public_image_urls.append(s)

        # Facebook has practical limits; keep it reasonable.
        public_image_urls = public_image_urls[:10]

        if public_image_urls:
            photo_url = _graph_url(f"{page_id}/photos", graph_version=graph_version)
            media_fbids: list[str] = []

            for image_url in public_image_urls:
                payload = {
                    "url": image_url,
                    "published": "false",
                    "access_token": page_access_token,
                }
                response = requests.post(photo_url, data=payload, timeout=15)
                if response.status_code != 200:
                    print(f"✗ Failed to upload photo to Facebook. Status: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                result = response.json() or {}
                fbid = result.get("id")
                if not fbid:
                    print("✗ Failed to upload photo to Facebook: missing id in response")
                    print(f"Response: {response.text}")
                    return False
                media_fbids.append(str(fbid))

            feed_url = _graph_url(f"{page_id}/feed", graph_version=graph_version)
            attached_media = [{"media_fbid": fbid} for fbid in media_fbids]
            payload = {
                "message": message,
                "attached_media": __import__("json").dumps(attached_media),
                "access_token": page_access_token,
            }
            response = requests.post(feed_url, data=payload, timeout=15)
            if response.status_code == 200:
                result = response.json() or {}
                post_id = result.get("id")
                print(
                    f"✓ Successfully posted property {property_instance.id} to Facebook with {len(media_fbids)} image(s): {post_id}"
                )
                return True
            else:
                print(f"✗ Failed to create feed post with photos. Status: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        else:
            # No image - post as text only
            url = _graph_url(f"{page_id}/feed", graph_version=graph_version)
            
            payload = {
                "message": message,
                "access_token": page_access_token,
            }
            
            response = requests.post(url, data=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id")
                print(f"✓ Successfully posted property {property_instance.id} to Facebook (no image): {post_id}")
                return True
            else:
                print(f"✗ Failed to post to Facebook. Status: {response.status_code}, Response: {response.text}")
                return False
            
    except Exception as e:
        print(f"✗ Error posting to Facebook: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@receiver(post_save, sender=Property)
def property_created_handler(sender, instance, created, **kwargs):
    """
    Signal handler that posts to Facebook when a new Property is created.
    Only triggers on creation (not updates).
    """
    if created:
        # Delay until after DB commit so related PropertyImage rows (created in the same request)
        # are visible to this process.
        def _do_post() -> None:
            try:
                prop = (
                    Property.objects.select_related("municipality")
                    .prefetch_related("images")
                    .get(pk=instance.pk)
                )
                post_to_facebook(prop)
            except Exception as e:
                # Don't let Facebook posting errors break property creation
                print(f"Error in Facebook posting handler: {str(e)}")

        transaction.on_commit(_do_post)
