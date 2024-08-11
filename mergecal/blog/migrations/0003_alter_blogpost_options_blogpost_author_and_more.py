# Generated by Django 5.0.3 on 2024-08-11 04:09

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_alter_blogpost_description"),
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="blogpost",
            options={
                "ordering": ["-pub_date", "title"],
                "verbose_name": "blog post",
                "verbose_name_plural": "blog posts",
            },
        ),
        migrations.AddField(
            model_name="blogpost",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="blog_posts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="author",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="keywords",
            field=models.CharField(
                blank=True,
                help_text="Comma-separated keywords for SEO",
                max_length=255,
                verbose_name="keywords",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="related_posts",
            field=models.ManyToManyField(
                blank=True, to="blog.blogpost", verbose_name="related posts"
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="tags",
            field=taggit.managers.TaggableManager(
                blank=True,
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="tags",
            ),
        ),
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(
                fields=["-pub_date", "title"], name="blog_blogpo_pub_dat_7b740c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(fields=["slug"], name="blog_blogpo_slug_361555_idx"),
        ),
    ]
