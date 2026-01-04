import os
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property


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
        f"🏡 NEW LISTING",
        f"━━━━━━━━━━━━━━━━",
        f"📋 {property_instance.title}",
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
        message_parts.append("📝 DESCRIPTION:")
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
    
    # Get all images
    images = list(property_instance.images.all())
    
    try:
        # If there are images, post with the first image using the photos endpoint
        if images and images[0].image:
            url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            
            payload = {
                "url": images[0].image,  # Use image URL
                "caption": message,
                "access_token": page_access_token,
            }
            
            response = requests.post(url, data=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id") or result.get("post_id")
                print(f"✓ Successfully posted property {property_instance.id} to Facebook with image: {post_id}")
                return True
            else:
                print(f"✗ Failed to post photo to Facebook. Status: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        else:
            # No image - post as text only
            url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
            
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
        # Post to Facebook asynchronously (in production, consider using Celery)
        # For now, we'll do it synchronously but catch any errors
        try:
            post_to_facebook(instance)
        except Exception as e:
            # Don't let Facebook posting errors break property creation
            print(f"Error in Facebook posting handler: {str(e)}")
