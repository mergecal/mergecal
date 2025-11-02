import logging

from django.views.generic import DetailView
from django.views.generic import ListView

from mergecalweb.core.logging_events import LogEvent

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
        extra = {"event": LogEvent.BLOG_POST_LIST_VIEW}
        if request.user.is_authenticated:
            extra["user_id"] = request.user.pk
            extra["email"] = request.user.email
        logger.info("Blog post list viewed", extra=extra)
        return super().get(request, *args, **kwargs)


class BlogPostDetailView(DetailView):
    model = BlogPost
    queryset = BlogPost.objects.filter(published=True)
    template_name = "blog/detail.html"
    context_object_name = "blog_post"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        blog_post = self.get_object()
        extra = {
            "event": LogEvent.BLOG_POST_DETAIL_VIEW,
            "blog_post_slug": blog_post.slug,
            "blog_post_title": blog_post.title,
        }
        if request.user.is_authenticated:
            extra["user_id"] = request.user.pk
            extra["email"] = request.user.email
        logger.info("Blog post viewed", extra=extra)
        return response


class BlogPostTagListView(ListView):
    model = BlogPost
    template_name = "blog/list.html"  # You can reuse the list template
    context_object_name = "blog_posts"

    def get_queryset(self):
        return BlogPost.objects.published().filter(tags__slug=self.kwargs["tag_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_tag"] = self.kwargs["tag_slug"]
        return context
