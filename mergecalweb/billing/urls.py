from django.urls import path

from mergecalweb.billing.views import ManageBillingView
from mergecalweb.billing.views import checkout_session_success

app_name = "billing"

urlpatterns = [
    path("manage-billing/", ManageBillingView.as_view(), name="manage_billing"),
    path(
        "success/",
        checkout_session_success,
        name="checkout_session_success",
    ),
]
