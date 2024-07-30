# ruff: noqa: ERA001

import logging

import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from djstripe.models import Price

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
        return ctx


class ManageBillingView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        customer = self.request.user.djstripe_customers.first()
        return_url = self.request.build_absolute_uri(
            reverse("users:detail", kwargs={"username": self.request.user.username}),
        )

        portal_session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=return_url,
        )
        return portal_session.url


class CheckoutRedirectView(TemplateView):
    template_name = "billing/checkout_redirect.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["stripe_public_key"] = settings.STRIPE_PUBLIC_KEY
        ctx["checkout_session_id"] = self.kwargs["session_id"]

        return ctx


checkout_redirect = CheckoutRedirectView.as_view()


class CreateCheckoutSession(RedirectView):
    """
    A view to create a new Checkout session

    Similar to this tutorial:
    https://stripe.com/docs/billing/subscriptions/checkout

    We create the session, then redirect to the CheckoutRedirectView.
    """

    def get_redirect_url(self, *args, **kwargs):
        price = Price.objects.filter(lookup_key="premiun_plan").first()
        if not price:
            msg = "You must first configure a price."
            raise ImproperlyConfigured(msg)

        checkout_session = stripe.checkout.Session.create(
            success_url="http://localhost:8000/checkout/success/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:8000/checkout/canceled/",
            mode="subscription",
            line_items=[{"price": price.id, "quantity": 1}],
            payment_method_types=["card"],
        )

        return reverse(
            "billing:checkout_redirect",
            kwargs={"session_id": checkout_session["id"]},
        )


class CheckoutSessionSuccessView(View):
    def get(self, request, *args, **kwargs):
        session_id = request.GET.get("session_id")
        if not session_id:
            return JsonResponse({"error": "No session ID provided."}, status=400)

        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            return JsonResponse(checkout_session, safe=False)
        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)


create_checkout_session = CreateCheckoutSession.as_view()
checkout_session_success = CheckoutSessionSuccessView.as_view()
