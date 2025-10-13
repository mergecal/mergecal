from __future__ import annotations

import logging
import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

    from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        is_open = getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
        logger.debug(
            "Auth: Signup check - is_open=%s, ip=%s",
            is_open,
            request.META.get("REMOTE_ADDR", "Unknown"),
        )
        return is_open

    def login(self, request, user):
        logger.info(
            "Auth: User login - username=%s, email=%s, tier=%s, ip=%s",
            user.username,
            user.email,
            user.subscription_tier,
            request.META.get("REMOTE_ADDR", "Unknown"),
        )
        return super().login(request, user)

    def logout(self, request):
        if request.user.is_authenticated:
            logger.info(
                "Auth: User logout - username=%s, ip=%s",
                request.user.username,
                request.META.get("REMOTE_ADDR", "Unknown"),
            )
        return super().logout(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        is_open = getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
        provider = sociallogin.account.provider
        logger.debug(
            "Auth: Social signup check - provider=%s, is_open=%s, ip=%s",
            provider,
            is_open,
            request.META.get("REMOTE_ADDR", "Unknown"),
        )
        return is_open

    def pre_social_login(self, request, sociallogin):
        """Log social login attempts"""
        provider = sociallogin.account.provider
        email = sociallogin.account.extra_data.get("email", "Unknown")

        logger.info(
            "Auth: Social login attempt - provider=%s, email=%s, ip=%s",
            provider,
            email,
            request.META.get("REMOTE_ADDR", "Unknown"),
        )
        return super().pre_social_login(request, sociallogin)

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict[str, typing.Any],
    ) -> User:
        """
        Populates user information from social provider info.

        See: https://docs.allauth.org/en/latest/socialaccount/advanced.html#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        provider = sociallogin.account.provider

        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"

        logger.info(
            "Auth: New social user - provider=%s, username=%s, email=%s, name=%s",
            provider,
            user.username,
            user.email,
            user.name,
        )

        return user
