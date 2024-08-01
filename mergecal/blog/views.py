from django.views.generic import DetailView
from django.views.generic import ListView

from .models import BlogPost


class BlogPostListView(ListView):
    model = BlogPost
    queryset = BlogPost.objects.filter(published=True)
    template_name = "blog/list.html"
    context_object_name = "blog_posts"
    paginate_by = 15  # that is all it takes to add pagination in a Class-Based View


class BlogPostDetailView(DetailView):
    model = BlogPost
    queryset = BlogPost.objects.filter(published=True)
    template_name = "blog/detail.html"
    context_object_name = "blog_post"
