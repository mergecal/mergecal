from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mergecalweb.core.emails import send_email

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_("Subscription"), {"fields": ("subscription_tier",)}),
    )
    list_display = [
        "email",
        "username",
        "name",
        "subscription_tier",
        "calendar_count_link",
        "is_superuser",
        "date_joined",
        "last_login",
    ]
    search_fields = ["name", "username", "email"]
    list_filter = ["is_superuser", "is_active", "subscription_tier"]
    ordering = ["-last_login"]

    def get_queryset(self, request):
        # Annotate each user with the count of calendars they own
        queryset = super().get_queryset(request)
        return queryset.annotate(calendar_count=Count("calendar"))

    @admin.display(description="Calendars")
    def calendar_count_link(self, obj):
        # Count is taken from the annotated _calendar_count in get_queryset
        count = obj.calendar_count
        url = (
            reverse("admin:calendars_calendar_changelist")
            + "?"
            + f"owner__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{} Calendars</a>', url, count)

    actions = [
        "send_feedback_email",
        "send_shorterm_rental_feedback_email",
        "send_nlnet_funding_email",
    ]

    @admin.action(description="Send feedback email")
    def send_feedback_email(self, request, queryset):
        for user in queryset:
            send_email(
                to_users=[user],
                subject="We'd love your feedback",
                bodies=[
                    (
                        "I hope you're enjoying MergeCal. I'd really "
                        "appreciate your feedback on the service."
                    ),
                    (
                        "Whether it's a feature suggestion, bug report, or "
                        "just your thoughts - I'd love to hear from you."
                    ),
                    "Just reply to this email and let me know what you think.",
                ],
                from_email="Abe <abe@mergecal.org>",
            )

        self.message_user(
            request,
            f"Feedback email sent to {queryset.count()} users",
            messages.SUCCESS,
        )

    @admin.action(description="Send shorterm rental feedback email")
    def send_shorterm_rental_feedback_email(self, request, queryset):
        for user in queryset:
            send_email(
                to_users=[user],
                subject="Feedback on short-term rental calendars",
                bodies=[
                    (
                        "I noticed you're using MergeCal for managing "
                        "short-term rental calendars."
                    ),
                    (
                        "I'm interested in how MergeCal is working for your "
                        "rental business. Are there specific features that "
                        "would make managing multiple rental calendars easier?"
                    ),
                    (
                        "Your feedback would be valuable in making MergeCal "
                        "better for property managers. Feel free to reply "
                        "with any thoughts or suggestions."
                    ),
                ],
                from_email="Abe <abe@mergecal.org>",
            )

        self.message_user(
            request,
            f"Short-term rental feedback email sent to {queryset.count()} users",
            messages.SUCCESS,
        )

    @admin.action(description="Send NLnet funding / anonymizer ask email")
    def send_nlnet_funding_email(self, request, queryset):
        for user in queryset:
            send_email(
                to_users=[user],
                subject="Helping make MergeCal more reliable \u2014 quick ask",
                bodies=[
                    (
                        "I wanted to share something exciting and ask if"
                        " you\u2019d be willing to help."
                    ),
                    (
                        "The Python library that powers MergeCal\u2019s"
                        " calendar merging just received funding from NLnet"
                        " \u2014 a nonprofit that supports open internet"
                        " infrastructure"
                        ' (<a href="https://nlnet.nl/project/OpenWebCalendar-recurring/">'
                        "https://nlnet.nl/project/OpenWebCalendar-recurring/</a>)."
                        " Part of that funding is going toward making the library"
                        " more reliable across different calendar apps and services,"
                        " and we need real-world test cases to do that well."
                    ),
                    (
                        "That\u2019s where the ask comes in: would you be open"
                        " to letting us use your MergeCal setup as a test case?"
                    ),
                    (
                        "A contributor built a privacy-focused anonymizer"
                        ' (<a href="https://github.com/mergecal/icalendar-anonymizer">'
                        "https://github.com/mergecal/icalendar-anonymizer</a>) that"
                        " would strip all personal details \u2014 names, descriptions,"
                        " locations \u2014 from your calendar sources and the merged"
                        " output, leaving only the structural data. We\u2019d use"
                        " that anonymized snapshot to verify the merge produces"
                        " consistent results over time. None of your actual data"
                        " would be retained."
                    ),
                    (
                        "It would be a genuine contribution to the open source"
                        " community \u2014 not just MergeCal, but anyone building"
                        " on top of the library."
                    ),
                    (
                        "No pressure at all, and happy to answer any questions"
                        " about how it works before you decide."
                    ),
                ],
                from_email="Abe <abe@mergecal.org>",
            )

        self.message_user(
            request,
            f"NLnet funding email sent to {queryset.count()} users",
            messages.SUCCESS,
        )
