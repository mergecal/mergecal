import pytest
from allauth.socialaccount.models import SocialLogin
from django.http import HttpRequest

from mergecalweb.users.adapters import AccountAdapter
from mergecalweb.users.adapters import SocialAccountAdapter
from mergecalweb.users.models import User


@pytest.mark.parametrize("allowed", [True, False])
def test_signup_follows_allow_registration_setting(settings, allowed):
    settings.ACCOUNT_ALLOW_REGISTRATION = allowed
    request = HttpRequest()

    assert AccountAdapter().is_open_for_signup(request) is allowed
    assert (
        SocialAccountAdapter().is_open_for_signup(request, SocialLogin(user=User()))
        is allowed
    )


@pytest.mark.parametrize(
    ("data", "expected_name"),
    [
        ({"name": "Ada Lovelace", "first_name": "Ada"}, "Ada Lovelace"),
        ({"first_name": "Ada", "last_name": "Lovelace"}, "Ada Lovelace"),
        ({"first_name": "Ada"}, "Ada"),
        ({"last_name": "Lovelace"}, ""),
        ({}, ""),
    ],
)
def test_social_signup_fills_name(data, expected_name):
    sociallogin = SocialLogin(user=User())

    user = SocialAccountAdapter().populate_user(HttpRequest(), sociallogin, data)

    assert user.name == expected_name


def test_social_signup_keeps_existing_name():
    sociallogin = SocialLogin(user=User(name="Existing Name"))

    user = SocialAccountAdapter().populate_user(
        HttpRequest(),
        sociallogin,
        {"name": "Provider Name"},
    )

    assert user.name == "Existing Name"
