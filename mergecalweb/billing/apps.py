from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecalweb.billing"
    verbose_name = "Billing"

    def ready(self):
        import mergecalweb.billing.signals  # noqa: F401
