# Generated by Django 5.0.3 on 2024-08-09 03:46

import django.db.models.deletion
import mergecal.calendars.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calendars", "0010_source_custom_prefix_source_exclude_keywords_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="calendar",
            name="calendar_file_str",
        ),
        migrations.AlterField(
            model_name="source",
            name="calendar",
            field=models.ForeignKey(
                help_text="The merged calendar this feed belongs to.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="calendarOf",
                to="calendars.calendar",
                verbose_name="Merged Calendar",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="custom_prefix",
            field=models.CharField(
                blank=True,
                help_text="Optional prefix to add before each event title from this feed (e.g., '[Work]').",
                max_length=50,
                verbose_name="Custom Prefix",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="exclude_keywords",
            field=models.TextField(
                blank=True,
                help_text="Enter keywords separated by commas. Events from this feed containing these keywords in their title will be excluded from the merged calendar.",
                verbose_name="Exclude Keywords",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="include_description",
            field=models.BooleanField(
                default=True,
                help_text="If checked, the event description from this feed will be included in the merged calendar.",
                verbose_name="Include Event Description",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="include_location",
            field=models.BooleanField(
                default=True,
                help_text="If checked, the event location from this feed will be included in the merged calendar.",
                verbose_name="Include Event Location",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="include_title",
            field=models.BooleanField(
                default=True,
                help_text="If checked, the original event title from this feed will be included in the merged calendar.",
                verbose_name="Include Event Title",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="name",
            field=models.CharField(
                help_text="A friendly name to identify this calendar feed.",
                max_length=255,
                verbose_name="Feed Name",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="url",
            field=models.URLField(
                help_text="The URL of the iCal feed for this calendar source.",
                max_length=400,
                validators=[mergecal.calendars.models.validate_ical_url],
                verbose_name="Feed URL",
            ),
        ),
    ]