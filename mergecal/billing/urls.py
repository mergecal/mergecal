from django.urls import path

from .views import checkout_redirect
from .views import checkout_session_success
from .views import create_checkout_session

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
]
