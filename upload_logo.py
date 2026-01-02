#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import cloudinary
import cloudinary.uploader

# Upload the logo
try:
    result = cloudinary.uploader.upload(
        'static/img/damcf-logo.png',
        folder='static',
        public_id='damcf-logo',
        overwrite=True
    )
    
    print('Logo uploaded successfully!')
    print('URL:', result['secure_url'])
    print('\nYou can use this URL in your templates.')
except Exception as e:
    print(f'Error uploading logo: {e}')
