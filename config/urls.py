from django.contrib import admin
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
