import re

import pytest
from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.urls import reverse


@pytest.mark.django_db
def test_confirming_email_after_signup_signs_the_user_in(client, settings):
    # Signing up schedules a follow-up email task; run it in-process so the
    # test doesn't need a Celery broker.
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client.post(
        reverse("account_signup"),
        {
            "email": "new-user@example.com",
            "username": "new-user",
            "password1": "a-long-test-passphrase",
            "password2": "a-long-test-passphrase",
        },
    )
    assert SESSION_KEY not in client.session
    [confirmation_url] = re.findall(
        r"https?://\S+/confirm-email/\S+/",
        "\n".join(message.body for message in mail.outbox),
    )

    client.post(confirmation_url)

    assert SESSION_KEY in client.session
