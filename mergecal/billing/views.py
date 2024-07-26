import stripe
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from djstripe.enums import APIKeyType
from djstripe.models import APIKey
from djstripe.models import Price

secret_api_key = APIKey.objects.filter(
    type=APIKeyType.secret,
).first()

if not secret_api_key:
    msg = "You must first configure a secret key."
    raise ImproperlyConfigured(msg)

stripe.api_key = secret_api_key.secret

public_keys = APIKey.objects.filter(type=APIKeyType.publishable)[:1]
if not public_keys.exists():
    msg = "You must first configure a public key."
    raise ImproperlyConfigured(msg)


class CheckoutRedirectView(TemplateView):
    template_name = "billing/checkout_redirect.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["stripe_public_key"] = public_keys.get().secret
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
