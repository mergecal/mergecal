"""Simple email utilities for MergeCal."""

import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from mergecalweb.users.models import User


def strip_html(text: str) -> str:
    """Remove HTML tags from text for plain text email version."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    return (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def send_email(
    *,
    to_users: list[User],
    subject: str,
    bodies: list[str],
    ps: str | None = None,
    from_email: str | None = None,
) -> int:
    """
    Send a transactional email using the base template.

    Args:
        to_users: List of User objects to send email to
        subject: Email subject line
        bodies: List of paragraph strings for the email body
        ps: Optional P.S. message
        from_email: Optional from email (defaults to settings.DEFAULT_FROM_EMAIL)

    Returns:
        Number of successfully sent emails
    """
    to_emails = [user.email for user in to_users]

    # Build context - use first user's name for greeting
    context = {
        "name": to_users[0].username if to_users else "there",
        "bodies": bodies,
        "ps": ps,
    }

    # Render HTML content
    html_content = render_to_string("emails/base.html", context)

    # Create plain text fallback with signature (strip HTML tags)
    plain_text_parts = [f"Hello {context['name']},\n"]
    plain_text_parts.extend([strip_html(body) for body in bodies])
    if ps:
        plain_text_parts.append(f"\nP.S. {strip_html(ps)}")

    # Add signature
    plain_text_parts.append(
        "\nBest regards,\n"
        "Abe Hanoka\n"
        "Creator of MergeCal.org\n"
        "abe@mergecal.org\n"
        "Connect with me: linkedin.com/in/abe101",
    )

    plain_text = "\n\n".join(plain_text_parts)

    # Create and send email
    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=to_emails,
    )
    email.attach_alternative(html_content, "text/html")

    return email.send()
