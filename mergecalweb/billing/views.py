# ruff: noqa: ERA001

import logging

import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from djstripe.models import Session

from mergecalweb.billing.signals import update_user_subscription_tier

logger = logging.getLogger(__name__)


stripe.api_key = settings.STRIPE_SECRET_KEY


class PricingTableView(TemplateView):
    template_name = "billing/pricing_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["price_table_id"] = settings.STRIPE_PRICE_TABLE_ID
        ctx["stripe_public_key"] = settings.STRIPE_PUBLIC_KEY
        if self.request.user.is_authenticated:
            customer = self.request.user.djstripe_customers.first()
            customer_session = stripe.CustomerSession.create(
                customer=customer.id,
                components={"pricing_table": {"enabled": True}},
            )
            ctx["customer_session_id"] = customer_session.client_secret
        logger.info("User %s accessed the pricing table view", self.request.user)
        return ctx


class ManageBillingView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        customer = self.request.user.djstripe_customers.first()
        # if self.request.user.is_free_tier:
        #     return reverse("pricing")

        return_url = self.request.build_absolute_uri(
            reverse("users:detail", kwargs={"username": self.request.user.username}),
        )
        logger.info("User %s accessed the manage billing view", self.request.user)

        portal_session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=return_url,
        )
        return portal_session.url


def checkout_session_success(request: HttpRequest) -> HttpResponse:
    if request.htmx:
        session_id = request.GET.get("session_id")

        if not session_id:
            return JsonResponse({"error": "No session ID provided."}, status=400)

        try:
            session: Session = Session._get_or_retrieve(session_id)  # noqa: SLF001
        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)

        update_user_subscription_tier(request.user, session.subscription)
        logger.info("retrieved session %s", session)
        context = {
            "session": session,
            "customer": session.customer,
            "subscription": session.subscription,
        }
        return render(request, "billing/_success.html", context)

    logger.info("User %s accessed the checkout session return view", request.user)
    return render(request, "billing/success.html")
