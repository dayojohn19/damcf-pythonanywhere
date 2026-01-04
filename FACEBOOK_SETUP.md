# Facebook Auto-Post Setup

This application automatically posts new property listings to your Facebook Page when they are created.

## Setup Instructions

### 1. Create a Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Choose "Business" as the app type
4. Fill in app details and create

### 2. Add Required Permissions to Your App

Before getting tokens, you need to add permissions to your app:

1. In your app dashboard, go to **"App Review"** → **"Permissions and Features"**
2. Search for and request these permissions (click "Request" next to each):
   - `pages_manage_posts` - Required to post to your page
   - `pages_read_engagement` - Optional, for analytics
3. Some permissions are granted immediately for your own pages

**OR use the simpler approach:**

1. Go to your app settings
2. Under **"Use cases"**, add **"Manage business extensions"** or **"Page management"**
3. This will give you the necessary permissions for pages you manage

### 3. Get Page Access Token

**Step 1: Generate User Token with Page Permissions**

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the "Meta App" dropdown
3. Click "Generate Access Token"
4. In the popup, select your Facebook Page
5. Click "Done" - you now have a user token with page access

**Step 2: Get the Permanent Page Token**

1. In Graph API Explorer, change the query to: `me/accounts`
2. Click "Submit"
3. You'll see a JSON response with your pages
4. Find your page in the `data` array
5. Copy the `access_token` value for your page (NOT the one at the top)
6. Copy the `id` value - this is your PAGE ID

**Example response:**
```json
{
  "data": [
    {
      "access_token": "EAABsbCS...ZD",  ← This is your PAGE ACCESS TOKEN (never expires!)
      "category": "Real Estate",
      "name": "Your Page Name",
      "id": "123456789",  ← This is your PAGE ID
      "tasks": ["ADVERTISE", "ANALYZE", "CREATE_CONTENT", "MODERATE", "MANAGE"]
    }
  ]
}
```

**Important:** The `access_token` inside the page object is a permanent page access token that never expires!

### 4. Get Your Page ID

If you didn't get it from step 3, your Page ID is shown in the `me/accounts` response. 

You can also find it here:
- Visit your Facebook Page → "About" section → scroll to find "Page ID"

### 5. Test Your Token (Important!)

1. Go to [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
2. Paste your Page Access Token (from the `me/accounts` response)
3. Click "Debug"
4. Check that:
   - Type is "Page Access Token"
   - It shows "Expires: Never" 
   - Your page name appears in the info
   - Scopes include posting permissions

### 6. Set Environment Variables on Heroku

```bash
heroku config:set FACEBOOK_PAGE_ACCESS_TOKEN="your_page_access_token_here"
heroku config:set FACEBOOK_PAGE_ID="your_page_id_here"
```

### 7. Test It

Create a new property listing through your admin panel or website. It should automatically post to Facebook!

## What Gets Posted

When a new property is created, the system posts:
- Property image (first image)
- Property title
- Price (formatted with peso sign)
- Location (municipality and address)
- Status (For Sale, For Rent, etc.)
- Description (full text, up to 500 characters)
- Contact information
- Direct link to property details
- Relevant hashtags

## Troubleshooting

### Token Issues
- **Token expired**: Page tokens from the Access Token Tool should never expire
- **Invalid token**: Make sure you copied the entire token without spaces
- **Wrong token type**: Use the PAGE token, not the user token

### Permission Issues
- Ensure you're an admin of the Facebook Page
- If you don't see your page, you may need to add it to your Business Manager first

### Posting Issues
- Check Heroku logs: `heroku logs --tail`
- Look for "Successfully posted property..." messages
- If you see errors, check the error message in the logs

### Common Errors
- **"Invalid OAuth access token"**: Token is wrong or expired
- **"Permissions error"**: You're not an admin of the page
- **"Image URL error"**: Make sure property has uploaded images to Cloudinary

## Security Notes

- Never commit access tokens to your repository
- Always use environment variables for sensitive credentials
- Regularly check token validity in Facebook Developer Console
- Tokens are tied to your app - if you delete the app, tokens become invalid

## Support

If you need help, check:
- [Facebook Platform Documentation](https://developers.facebook.com/docs/)
- [Facebook Community Forum](https://developers.facebook.com/community/)
- Contact: damcfrealtyinc@gmail.com
