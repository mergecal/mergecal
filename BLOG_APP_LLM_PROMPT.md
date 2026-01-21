# Prompt: Create a Reusable Django Blog App

Create a complete, production-ready, reusable Django blog app package called `django-bootstrap-blog` that can be installed via pip and dropped into any Django project. This should be an opinionated, batteries-included solution.

## Package Requirements

### Structure
```
django-bootstrap-blog/
├── pyproject.toml
├── setup.py (for backwards compatibility)
├── README.md
├── LICENSE (MIT)
├── MANIFEST.in
├── bootstrap_blog/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── sitemaps.py
│   ├── settings.py
│   ├── templates/
│   │   └── bootstrap_blog/
│   │       ├── base.html
│   │       ├── list.html
│   │       └── detail.html
│   ├── static/
│   │   └── bootstrap_blog/
│   │       ├── css/
│   │       │   └── blog.css
│   │       └── js/
│   │           └── blog.js
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── blog_tags.py
│   ├── migrations/
│   │   └── __init__.py
│   └── management/
│       └── commands/
│           └── create_sample_posts.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    └── test_admin.py
```

## Core Features to Include

### Models (models.py)

Create a `BlogPost` model with:
- **title**: CharField(max_length=255)
- **slug**: AutoSlugField (using django-autoslug)
- **author**: ForeignKey to `settings.AUTH_USER_MODEL` (optional, nullable)
- **image**: ImageField (optional, upload_to='blog/')
- **text**: RichTextField (using django-ckeditor)
- **description**: TextField (for meta description/preview)
- **keywords**: CharField (for SEO keywords)
- **published**: BooleanField (default=False)
- **pub_date**: DateTimeField (auto-set when published)
- **tags**: TaggableManager (using django-taggit)
- **related_posts**: ManyToManyField to self
- **created**: DateTimeField(auto_now_add=True)
- **modified**: DateTimeField(auto_now=True)

Include a custom `BlogPostQueryset` with:
- `published()` method - filters published posts with pub_date <= now
- `draft()` method - filters unpublished posts

Model methods:
- `get_absolute_url()` - returns URL to detail view
- `get_reading_time()` - calculates reading time (200 words/min)
- `get_related_posts()` - returns up to 3 published related posts
- `is_published` property - checks if published and pub_date is in past
- `keyword_list` property - returns list of keywords from comma-separated string

Override `save()` to auto-set `pub_date` when published becomes True, and clear it when set to False.

### Views (views.py)

Create class-based views:
1. **BlogPostListView** - ListView with pagination (15 per page)
2. **BlogPostDetailView** - DetailView for single post
3. **BlogPostTagListView** - ListView filtered by tag slug

All views should only show published posts.

### URLs (urls.py)

```python
app_name = "bootstrap_blog"

urlpatterns = [
    path("", BlogPostListView.as_view(), name="list"),
    path("<slug:slug>/", BlogPostDetailView.as_view(), name="detail"),
    path("tag/<slug:tag_slug>/", BlogPostTagListView.as_view(), name="tag"),
]
```

### Admin (admin.py)

Create a comprehensive `BlogPostAdmin` with:
- list_display: title, author, published, pub_date, created, modified
- list_filter: published, pub_date, tags
- search_fields: title, text, description
- prepopulated_fields: slug from title
- date_hierarchy: pub_date
- filter_horizontal: related_posts
- Fieldsets organized into sections

### Templates

**bootstrap_blog/base.html**:
- Minimal base that expects a `base.html` to extend from parent project
- Define blocks for: title, meta_description, meta_keywords, og_title, og_description, og_image, content
- Include Bootstrap 5 and Bootstrap Icons
- Clean, semantic HTML5

**bootstrap_blog/list.html**:
- Extend base.html
- Show grid of blog post cards (3 columns on large screens, 2 on medium, 1 on small)
- Each card shows: image (if exists), title, description (truncated), tags, pub_date, author, reading time
- Include pagination controls
- Breadcrumb navigation
- Schema.org markup for Blog
- Empty state message

**bootstrap_blog/detail.html**:
- Extend base.html
- Full blog post with image at top
- Header with title, pub_date, reading time, author, tags
- Auto-generated table of contents from h2/h3 headers
- Blog content with styling
- Social share buttons (Facebook, Twitter, LinkedIn, WhatsApp, Telegram)
- Author bio section (if author exists)
- Related posts section (if any)
- Schema.org markup for BlogPosting
- Include Prism.js for code syntax highlighting
- JavaScript to generate TOC from headers

### CSS (static/bootstrap_blog/css/blog.css)

Include custom styles for:
- Card hover effects
- Blog content typography
- Code block styling
- Responsive images
- Table of contents styling
- Social share button styling

### Sitemaps (sitemaps.py)

Create `BlogSitemap` class:
- changefreq: 'weekly'
- priority: 0.9
- Returns published posts
- lastmod: use modified date

### App Settings (settings.py)

Configurable settings with sensible defaults:
```python
BOOTSTRAP_BLOG_PAGINATE_BY = getattr(settings, 'BOOTSTRAP_BLOG_PAGINATE_BY', 15)
BOOTSTRAP_BLOG_READING_SPEED = getattr(settings, 'BOOTSTRAP_BLOG_READING_SPEED', 200)
BOOTSTRAP_BLOG_RELATED_POSTS_COUNT = getattr(settings, 'BOOTSTRAP_BLOG_RELATED_POSTS_COUNT', 3)
BOOTSTRAP_BLOG_ALLOW_ANONYMOUS_AUTHORS = getattr(settings, 'BOOTSTRAP_BLOG_ALLOW_ANONYMOUS_AUTHORS', True)
```

### Management Command

Create `create_sample_posts.py` command that generates 5-10 sample blog posts with lorem ipsum content for testing.

## Dependencies (pyproject.toml)

```toml
[project]
name = "django-bootstrap-blog"
version = "1.0.0"
description = "A batteries-included, Bootstrap 5 blog app for Django"
requires-python = ">=3.9"
dependencies = [
    "Django>=4.0",
    "django-autoslug>=1.9.9",
    "django-ckeditor>=6.7.0",
    "django-taggit>=6.0.0",
    "django-social-share>=2.3.0",
    "Pillow>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-django>=4.5",
    "pytest-cov>=4.0",
]
```

## Documentation (README.md)

Include:
1. **Installation instructions**:
   ```bash
   pip install django-bootstrap-blog
   ```

2. **Quick start**:
   ```python
   # settings.py
   INSTALLED_APPS = [
       ...
       'django.contrib.sites',
       'django.contrib.sitemaps',
       'ckeditor',
       'taggit',
       'bootstrap_blog',
   ]

   # urls.py
   from bootstrap_blog.sitemaps import BlogSitemap

   sitemaps = {
       'blog': BlogSitemap,
   }

   urlpatterns = [
       path('blog/', include('bootstrap_blog.urls')),
       path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
   ]
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   python manage.py create_sample_posts  # Optional: create sample data
   ```

4. **Customization guide**:
   - How to override templates
   - How to customize settings
   - How to extend models (abstract base class pattern)

5. **Template blocks available**:
   - List all template blocks that can be overridden

6. **Requirements**:
   - Needs a `base.html` template in parent project
   - Bootstrap 5 should be included in parent project
   - Bootstrap Icons should be included

## Key Implementation Details

- Use `get_user_model()` for author field to support custom user models
- Make author field nullable (`null=True, blank=True`) and optional
- Auto-generate slug from title using AutoSlugField
- Use timezone-aware datetimes
- Include comprehensive docstrings
- Add database indexes for performance (pub_date, slug)
- Use `auto_now_add` and `auto_now` for timestamps
- Include `__str__` methods for all models
- Use verbose_name and verbose_name_plural in Meta
- Include translation-ready strings with `gettext_lazy`
- Ensure all views only show published posts (published=True, pub_date<=now)

## Testing

Include basic tests for:
- Model creation and methods
- QuerySet methods (published, draft)
- Views (list, detail, tag filtering)
- URL routing
- Admin registration

## Additional Nice-to-Haves

1. Template tags for:
   - `{% recent_posts count=5 %}`
   - `{% popular_tags %}`
   - `{% blog_archive %}` (posts grouped by year/month)

2. RSS/Atom feed support

3. Comment system (optional, can be disabled)

4. Draft preview for authenticated staff users

Make this production-ready, well-documented, and easy to drop into any Django project with Bootstrap 5.
