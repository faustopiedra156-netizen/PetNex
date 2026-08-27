from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PaginasPublicasSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return ['home', 'servicios', 'contacto', 'terminos_condiciones', 'politica_privacidad']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == 'home' else 0.7
