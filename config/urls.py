from django.contrib import admin
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_url

from django.conf import settings
from django.conf.urls.static import static

from core import views as core_views
from core.sitemaps import StaticViewSitemap, PropertySitemap, MunicipalitySitemap, ServiceSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'properties': PropertySitemap,
    'municipalities': MunicipalitySitemap,
    'services': ServiceSitemap,
}

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(url=static_url("img/damcf-logo.png"), permanent=True),
        name="favicon",
    ),
    path("admin/", admin.site.urls),
    path("accounts/logout/", core_views.logout_view, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "google48bcdfe5ffff5f5a.html",
        TemplateView.as_view(template_name="core/google48bcdfe5ffff5f5a.html"),
        name="google_site_verification",
    ),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path("", include("core.urls")),
]

# Serve local media from Django only in development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
