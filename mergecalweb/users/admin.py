from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.core.mail import EmailMessage
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mergecalweb.core.constants import MailjetTemplates

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

    actions = ["send_feedback_email", "send_shorterm_rental_feedback_email"]

    @admin.action(description="Send feedback email")
    def send_feedback_email(self, request, queryset):
        message = EmailMessage(
            to=[user.email for user in queryset],
        )
        message.template_id = MailjetTemplates.FEEDBACK
        message.from_email = None

        # Prepare merge data for all recipients
        message.merge_data = {user.email: {"name": user.name} for user in queryset}

        # Send the message
        message.send()

        self.message_user(
            request,
            f"Feedback email sent to {queryset.count()} users",
            messages.SUCCESS,
        )

    @admin.action(description="Send shorterm rental feedback email")
    def send_shorterm_rental_feedback_email(self, request, queryset):
        message = EmailMessage(
            to=[user.email for user in queryset],
        )
        message.template_id = MailjetTemplates.SHORTERM_RENTAL_FEEDBACK
        message.from_email = None

        # Prepare merge data for all recipients
        message.merge_data = {user.email: {"name": user.name} for user in queryset}

        # Send the message
        message.send()

        self.message_user(
            request,
            f"Feedback email sent to {queryset.count()} users",
            messages.SUCCESS,
        )
