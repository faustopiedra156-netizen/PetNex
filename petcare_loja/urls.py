from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView

from citas.sitemaps import PaginasPublicasSitemap

sitemaps = {'publicas': PaginasPublicasSitemap}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    # This route is loaded while Django runs system checks, before collectstatic.
    # Do not resolve it through the manifest-backed staticfiles storage here.
    path('favicon.ico', RedirectView.as_view(url=f'{settings.STATIC_URL}img/favicon.svg', permanent=True)),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('citas.urls')),
]

# Media local para desarrollo. En producción debe usarse almacenamiento de objetos.
if not settings.IS_RENDER:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
