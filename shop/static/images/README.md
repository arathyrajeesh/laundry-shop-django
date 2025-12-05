# Static Images Directory

This directory contains all the static images used in the laundry shop website.

## Required Images:

### Logo & Branding
- `Shine.png` - Logo for the navbar (should be square, around 40x40px)

### Hero Section
- `hero2.jpg` - Background image for the hero section (recommended: 1920x1080px or larger)

### About Section
- `about.png` - Image for the about section (recommended: 480x400px)

### Services Section
- `laundry.webp` - Wash & Fold Laundry service image
- `drycleaning.webp` - Dry Cleaning service image
- `carpet.jpg` - Carpet Cleaning service image
- `formal.png` - Suit & Formal Wear service image
- `iron.jpg` - Folding & Ironing service image

## How to Add Images:

1. Place your image files in this directory
2. Make sure filenames match exactly as referenced in the templates
3. Supported formats: JPG, PNG, WebP, GIF
4. For best performance, optimize images before uploading

## Image Optimization Tips:

- Use WebP format for better compression
- Resize images to the actual display size
- Compress images using tools like TinyPNG or ImageOptim
- Use descriptive alt text in templates

## Current Template References:

The home.html template references these images using Django's static template tag:
```html
{% load static %}
<img src="{% static 'images/filename.ext' %}" alt="Description">
```

For background images:
```html
style="background: url('{% static 'images/filename.ext' %}') no-repeat center center/cover;"