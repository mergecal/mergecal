# ruff: noqa: PLR0913, FBT002
# your_app/emails.py

from django.core.mail import EmailMessage

from mergecal.core.constants import MailjetTemplates


class TemplateEmailMessage(EmailMessage):
    DEFAULT_TEMPLATE_ID = MailjetTemplates.BASE

    def __init__(
        self,
        subject="",
        body="",
        from_email=None,
        to=None,
        bcc=None,
        connection=None,
        attachments=None,
        headers=None,
        cc=None,
        reply_to=None,
        template_id=None,
        context=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            subject,
            body,
            from_email,
            to,
            bcc,
            connection,
            attachments,
            headers,
            cc,
            reply_to,
            *args,
            **kwargs,
        )
        self.template_id = template_id or self.DEFAULT_TEMPLATE_ID
        self.context = context or {}

    def send(self, fail_silently=False):
        if not isinstance(self.context, dict):
            msg = "Context must be a dictionary with recipient emails as keys."
            raise TypeError(msg)

        self.merge_data = {
            recipient: self.context.get(recipient, {}) for recipient in self.to
        }
        super().send(fail_silently=fail_silently)
