from django.urls import path

from mergecal.billing.views import ManageBillingView
from mergecal.billing.views import checkout_redirect
from mergecal.billing.views import checkout_session_success
from mergecal.billing.views import create_checkout_session

app_name = "billing"

urlpatterns = [
    path(
        "checkout/redirect/<str:session_id>",
        checkout_redirect,
        name="checkout_redirect",
    ),
    path("checkout/create/", create_checkout_session, name="create_checkout_session"),
    path(
        "checkout/success/",
        checkout_session_success,
        name="checkout_session_success",
    ),
    path("manage-billing/", ManageBillingView.as_view(), name="manage_billing"),
]
