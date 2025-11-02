"""Tests for core functionality."""

import pytest
from django.core import mail

from mergecalweb.billing.emails import downgrade_subscription_email
from mergecalweb.billing.emails import send_trial_ending_email
from mergecalweb.billing.emails import upgrade_subscription_email
from mergecalweb.core.emails import send_email
from mergecalweb.users.models import User


@pytest.mark.django_db
class TestEmailSystem:
    """Test that email system works correctly."""

    def test_send_email_basic(self, user: User):
        """Test basic email sending."""
        send_email(
            to_users=[user],
            subject="Test Subject",
            bodies=["This is a test email.", "Second paragraph."],
            ps="Test P.S.",
            from_email="test@mergecal.org",
        )

        # Check that one message has been sent
        assert len(mail.outbox) == 1

        # Verify email details
        sent_email = mail.outbox[0]
        assert sent_email.subject == "Test Subject"
        assert user.email in sent_email.to
        assert "test@mergecal.org" in sent_email.from_email

        # Check that HTML alternative is present
        assert len(sent_email.alternatives) == 1
        html_content, content_type = sent_email.alternatives[0]
        assert content_type == "text/html"
        assert "MergeCal" in html_content
        assert "This is a test email." in html_content
        assert "Test P.S." in html_content

    def test_upgrade_subscription_email_new_user(self, user: User):
        """Test upgrade email for new user skips (welcome sent via signup)."""
        # User was just created, so should skip sending
        result = upgrade_subscription_email(user, User.SubscriptionTier.PERSONAL)

        # Should return 0 (no email sent)
        assert result == 0
        # No email should be sent (welcome is handled by allauth signal)
        assert len(mail.outbox) == 0

    def test_upgrade_subscription_email_existing_user(self, user: User):
        """Test upgrade email for existing user."""
        # Make user appear to be created over 2 hours ago
        import datetime

        from django.utils import timezone

        user.date_joined = timezone.now() - datetime.timedelta(hours=2)
        user.save()

        upgrade_subscription_email(user, User.SubscriptionTier.PERSONAL)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]

        # Should receive tier change email
        assert "Personal" in sent_email.subject
        assert user.email in sent_email.to
        assert "abe@mergecal.org" in sent_email.from_email

        html_content = sent_email.alternatives[0][0]
        assert "upgrade" in html_content.lower() or "active" in html_content.lower()
        assert "Abe Hanoka" in html_content
        assert "linkedin.com/in/abe101" in html_content

    def test_downgrade_subscription_email(self, user: User):
        """Test downgrade subscription email sends correctly."""
        downgrade_subscription_email(user)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert "subscription has been updated" in sent_email.subject
        assert user.email in sent_email.to
        assert len(sent_email.alternatives) == 1

    def test_trial_ending_email(self, user: User):
        """Test trial ending email sends correctly."""
        send_trial_ending_email(user)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert "trial is ending soon" in sent_email.subject
        assert user.email in sent_email.to
        assert len(sent_email.alternatives) == 1

    def test_email_has_plain_text_fallback(self, user: User):
        """Test that emails include plain text fallback."""
        # Make user appear to be created over 2 hours ago
        import datetime

        from django.utils import timezone

        user.date_joined = timezone.now() - datetime.timedelta(hours=2)
        user.save()

        upgrade_subscription_email(user, User.SubscriptionTier.SUPPORTER)

        sent_email = mail.outbox[0]
        # Plain text body should not be empty
        assert sent_email.body
        assert len(sent_email.body) > 0

    def test_email_signature_format(self, user: User):
        """Test that email signature has the correct format."""
        send_email(
            to_users=[user],
            subject="Test",
            bodies=["Test body"],
            from_email="abe@mergecal.org",
        )

        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0]

        # Check signature components in HTML
        assert "Best regards," in html_content
        assert "Abe Hanoka" in html_content
        assert "MergeCal.org" in html_content
        assert "abe@mergecal.org" in html_content
        assert "linkedin.com/in/abe101" in html_content

        # Check signature components in plain text
        assert "Best regards," in sent_email.body
        assert "Abe Hanoka" in sent_email.body
        assert "MergeCal.org" in sent_email.body
        assert "abe@mergecal.org" in sent_email.body
        assert "linkedin.com/in/abe101" in sent_email.body

    def test_email_logo_in_html(self, user: User):
        """Test that email includes logo image."""
        send_email(
            to_users=[user],
            subject="Test",
            bodies=["Test body"],
            from_email="abe@mergecal.org",
        )

        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0]

        # Check logo image is present
        assert "favicon-no-boarder.png" in html_content
        assert 'alt="MergeCal"' in html_content
