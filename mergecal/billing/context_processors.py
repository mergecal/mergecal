import typing

from django.utils import timezone

if typing.TYPE_CHECKING:
    from djstripe.models import Customer
    from djstripe.models import PaymentMethod
    from djstripe.models import Subscription


def trial_status(request):
    if request.user.is_authenticated:
        # Assuming you have a UserProfile model with a trial_end_date field
        customer: Customer = request.user.djstripe_customers.first()
        if not customer:
            return {"is_trial": False, "trial_days_left": 0}
        subscription: Subscription = customer.subscriptions.filter(
            status="trialing",
        ).first()
        if not subscription:
            return {"is_trial": False, "trial_days_left": 0}
        payment_method: PaymentMethod = customer.default_payment_method

        if subscription.status == "trialing" and not payment_method:
            trial_end_date = subscription.trial_end
            days_left = (trial_end_date - timezone.now()).days
            is_trial = days_left > 0
            return {"is_trial": is_trial, "trial_days_left": max(0, days_left)}
    return {"is_trial": False, "trial_days_left": 0}
