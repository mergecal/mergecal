# ruff: noqa: PLR0913, FBT002, FBT001
# your_app/emails.py

from django.core.mail import EmailMessage

from mergecal.core.constants import MailjetTemplates
from mergecal.users.models import User


class TemplateEmailMessage(EmailMessage):
    DEFAULT_TEMPLATE_ID = MailjetTemplates.BASE

    def __init__(
        self,
        subject: str,
        to_users: list[User],
        body: str,
        from_email: str | None = None,
        template_id: str | None = None,
    ):
        # Extract email addresses from the user queryset
        to_emails = [user.email for user in to_users]
        # Initialize the parent class with the necessary parameters
        super().__init__(
            subject=subject,
            body="",
            from_email=from_email,
            to=to_emails,
        )

        # Set the template ID and context for each recipient
        self.template_id = template_id or self.DEFAULT_TEMPLATE_ID
        self.context = {
            user.email: {"name": user.username, "body": body} for user in to_users
        }

    def send(self, fail_silently: bool = False) -> int:
        if not isinstance(self.context, dict):
            msg = "Context must be a dictionary with recipient emails as keys."
            raise TypeError(msg)

        # Set merge_data for each recipient
        self.merge_data = {
            recipient: self.context.get(recipient, {}) for recipient in self.to
        }
        # Send the email
        return super().send(fail_silently=fail_silently)
