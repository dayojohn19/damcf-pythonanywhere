# Facebook Auto-Post Setup

This application automatically posts new property listings to your Facebook Page when they are created.

## Setup Instructions

### 1. Create a Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app or use an existing one
3. Add the "Facebook Login" product to your app

### 2. Get a Page Access Token

1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. Click "Generate Access Token"
4. Grant permissions:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
5. Copy the short-lived token

### 3. Convert to Long-Lived Token

Use this URL (replace `YOUR_APP_ID`, `YOUR_APP_SECRET`, and `SHORT_LIVED_TOKEN`):

```
https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN
```

This returns a long-lived User Access Token (valid for 60 days).

### 4. Get a Page Access Token (Never Expires)

Use the long-lived user token to get a page token:

```
https://graph.facebook.com/v18.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN
```

Find your page in the response and copy its `access_token`. This token never expires (as long as the app remains active).

### 5. Get Your Page ID

Your page ID is in the same response from step 4, or:
- Go to your Facebook Page
- Click "About"
- Scroll down to find "Page ID"

### 6. Set Environment Variables on Heroku

```bash
heroku config:set FACEBOOK_PAGE_ACCESS_TOKEN="your_page_access_token_here"
heroku config:set FACEBOOK_PAGE_ID="your_page_id_here"
```

### 7. Test It

Create a new property listing through your admin panel or website. It should automatically post to Facebook!

## What Gets Posted

When a new property is created, the system posts:
- Property title
- Location (municipality)
- Address (if available)
- Price (if available)
- Status (For Sale, For Rent, etc.)
- Description (truncated if long)
- Direct link to property details
- First property image (if available)
- Relevant hashtags

## Troubleshooting

- Check Heroku logs: `heroku logs --tail`
- Ensure your Page Access Token has the correct permissions
- Make sure the token hasn't expired (page tokens shouldn't expire)
- Test your token at [Facebook Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)

## Security Notes

- Never commit access tokens to your repository
- Always use environment variables for sensitive credentials
- Regularly check token validity in Facebook Developer Console
