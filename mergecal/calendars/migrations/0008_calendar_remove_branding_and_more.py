# Generated by Django 5.0.3 on 2024-07-31 18:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calendars", "0007_alter_source_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendar",
            name="remove_branding",
            field=models.BooleanField(
                default=False,
                help_text="Remove MergeCal branding from the calendar. Only available for Business tier and above.",
                verbose_name="Remove MergeCal Branding",
            ),
        ),
        migrations.AddField(
            model_name="calendar",
            name="update_frequency_seconds",
            field=models.PositiveIntegerField(
                default=43200,
                help_text="How often the calendar updates in seconds. Default is every 12 hours (43200 seconds).",
                verbose_name="Update Frequency",
            ),
        ),
    ]