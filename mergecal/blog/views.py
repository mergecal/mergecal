import logging

from django.views.generic import DetailView
from django.views.generic import ListView

from .models import BlogPost

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BlogPostListView(ListView):
    model = BlogPost
    queryset = BlogPost.objects.filter(published=True)
    template_name = "blog/list.html"
    context_object_name = "blog_posts"
    paginate_by = 15  # that is all it takes to add pagination in a Class-Based View

    def get(self, request, *args, **kwargs):
        logger.info(
            "BlogPostListView visited by user: %s from IP: %s",
            request.user,
            request.META.get("REMOTE_ADDR"),
        )
        return super().get(request, *args, **kwargs)


class BlogPostDetailView(DetailView):
    model = BlogPost
    queryset = BlogPost.objects.filter(published=True)
    template_name = "blog/detail.html"
    context_object_name = "blog_post"

    def get(self, request, *args, **kwargs):
        logger.info(
            "BlogPostDetailView visited by user: %s from IP: %s",
            request.user,
            request.META.get("REMOTE_ADDR"),
        )
        return super().get(request, *args, **kwargs)
