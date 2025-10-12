# ruff: noqa
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from django.views.generic.base import RedirectView
from mergecalweb.billing.views import PricingTableView
from mergecalweb.blog.sitemaps import BlogSitemap
from mergecalweb.calendars.views import url_validator
from mergecalweb.core.sitemaps import StaticViewSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    path(
        "meetup/",
        TemplateView.as_view(template_name="pages/meetup.html"),
        name="meetup",
    ),
    path(
        "discord/",
        TemplateView.as_view(template_name="pages/discord.html"),
        name="discord",
    ),
    path(
        "twitch/",
        TemplateView.as_view(template_name="pages/twitch.html"),
        name="twitch",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("mergecalweb.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path(
        "calendars/",
        include("mergecalweb.calendars.urls", namespace="calendars"),
        name="calendars",
    ),
    path("billing/", include("mergecalweb.billing.urls", namespace="billing")),
    path("pricing/", PricingTableView.as_view(), name="pricing"),
    path("blog/", include("mergecalweb.blog.urls", namespace="blog")),
    path("validator/", url_validator, name="url_validator"),
    path("tz_detect/", include("tz_detect.urls")),
    path(
        "privacy/",
        TemplateView.as_view(template_name="pages/privacy.html"),
        name="privacy",
    ),
    path(
        "terms/",
        TemplateView.as_view(template_name="pages/terms.html"),
        name="terms",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),  # add the robots.txt file
    path(
        "favicon.png",
        RedirectView.as_view(url="/static/images/favicon.png", permanent=True),
    ),
    path(
        "favicon.ico",
        RedirectView.as_view(url="static/images/favicons/favicon.ico", permanent=True),
    ),
    path(
        "cc091514c16021fa4fcd472803a63e5f.txt",
        TemplateView.as_view(
            template_name="cc091514c16021fa4fcd472803a63e5f.txt",
            content_type="text/plain",
        ),
    ),
    path("djstripe/", include("djstripe.urls", namespace="djstripe")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
