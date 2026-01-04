from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Property, Municipality, Service


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return ['core:home', 'core:listings', 'core:agents', 'core:services', 'core:municipalities', 'core:contact']

    def location(self, item):
        return reverse(item)


class PropertySitemap(Sitemap):
    """Sitemap for property listings"""
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Property.objects.filter(status__in=['for_sale', 'for_lease', 'for_rent'])

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('core:property_detail', args=[obj.pk])


class MunicipalitySitemap(Sitemap):
    """Sitemap for municipalities"""
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Municipality.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # Assuming you have a municipality detail page
        return f"/municipalities/?filter={obj.name}"


class ServiceSitemap(Sitemap):
    """Sitemap for services"""
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Service.objects.filter(active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('core:services')
