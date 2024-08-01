from django.urls import path

from .views import BlogPostDetailView
from .views import BlogPostListView

app_name = "blog"

urlpatterns = [
    path("", BlogPostListView.as_view(), name="list"),
    path("<slug>", BlogPostDetailView.as_view(), name="detail"),
]
