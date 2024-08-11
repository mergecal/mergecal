from autoslug.fields import AutoSlugField
from ckeditor.fields import RichTextField
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager

from mergecal.core.models import TimeStampedModel

User = get_user_model()


class BlogPostQueryset(models.QuerySet):
    def published(self):
        return self.filter(published=True, pub_date__lte=timezone.now())

    def draft(self):
        return self.filter(published=False)


class BlogPost(TimeStampedModel):
    title = models.CharField(_("title"), max_length=255)
    slug = AutoSlugField(_("slug"), populate_from="title", unique=True)
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
        verbose_name=_("author"),
    )
    image = models.ImageField(_("image"), blank=True, null=True, upload_to="blog")
    text = RichTextField(_("text"))
    description = models.TextField(_("description"), default="")
    keywords = models.CharField(
        _("keywords"),
        max_length=255,
        blank=True,
        help_text=_("Comma-separated keywords for SEO"),
    )
    published = models.BooleanField(_("published"), default=False)
    pub_date = models.DateTimeField(_("publish date"), blank=True, null=True)
    tags = TaggableManager(_("tags"), blank=True)
    related_posts = models.ManyToManyField(
        "self",
        verbose_name=_("related posts"),
        blank=True,
        symmetrical=False,
    )

    objects = BlogPostQueryset.as_manager()

    class Meta:
        verbose_name = _("blog post")
        verbose_name_plural = _("blog posts")
        ordering = ["-pub_date", "title"]
        indexes = [
            models.Index(fields=["-pub_date", "title"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.published and self.pub_date is None:
            self.pub_date = timezone.now()
        elif not self.published and self.pub_date is not None:
            self.pub_date = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    def get_reading_time(self):
        word_count = len(self.text.split())
        minutes = word_count // 200  # Assuming 200 words per minute
        return max(1, minutes)  # Minimum 1 minute reading time

    def get_related_posts(self):
        return self.related_posts.filter(published=True, pub_date__lte=timezone.now())[
            :3
        ]

    @property
    def is_published(self):
        return self.published and self.pub_date and self.pub_date <= timezone.now()

    @property
    def keyword_list(self):
        return [
            keyword.strip() for keyword in self.keywords.split(",") if keyword.strip()
        ]
