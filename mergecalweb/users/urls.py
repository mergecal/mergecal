from django.urls import path

from .views import account_delete_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~delete/", view=account_delete_view, name="delete"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
