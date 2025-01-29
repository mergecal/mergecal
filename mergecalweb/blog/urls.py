from django.urls import path

from .views import BlogPostDetailView
from .views import BlogPostListView
from .views import BlogPostTagListView

app_name = "blog"

urlpatterns = [
    path("", BlogPostListView.as_view(), name="list"),
    path("<slug>", BlogPostDetailView.as_view(), name="detail"),
    path("tag/<slug:tag_slug>/", BlogPostTagListView.as_view(), name="tag"),
]
