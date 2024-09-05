# ruff: noqa: PLR0913, FBT002, FBT001
# your_app/emails.py
from django.conf import settings
from django.core.mail import EmailMessage

from mergecal.core.constants import MailjetTemplates
from mergecal.users.models import User

THREE = 3
FOUR = 4


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


class MultiBodyTemplateEmailMessage(EmailMessage):
    DEFAULT_TEMPLATE_ID = MailjetTemplates.BASE

    def __init__(
        self,
        subject: str,
        to_users: list[User],
        bodies: list[str],
        ps: str | None = None,
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

        if settings.DEBUG:
            self.body = "\n\n".join(bodies[0])
            if ps:
                self.body += f"\n\nPS: {ps}"
        if template_id:
            self.template_id = template_id
        elif len(bodies) == THREE:
            self.template_id = MailjetTemplates.THREE_PARAGRAPHS
        elif len(bodies) == FOUR:
            self.template_id = MailjetTemplates.FOUR_PARAGRAPHS
        else:
            self.template_id = self.DEFAULT_TEMPLATE_ID

        # Set the context for each recipient
        self.context = {user.email: {"name": user.username} for user in to_users}

        # Add body fields to context based on the number of bodies
        for i, body in enumerate(bodies, start=1):
            for email in self.context:
                self.context[email][f"body{i}"] = body
                if ps:
                    self.context[email]["ps"] = ps

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
