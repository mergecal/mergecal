from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return ["home", "about", "pricing", "privacy", "terms"]

    def location(self, item):
        return reverse(item)
