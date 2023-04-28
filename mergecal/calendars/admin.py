from django.contrib import admin

from .models import Calendar, Source


class CommentInline(admin.TabularInline):
    model = Source


class CalendarAdmin(admin.ModelAdmin):
    inlines = [
        CommentInline,
    ]


admin.site.register(Calendar, CalendarAdmin)
admin.site.register(Source)
