# In a new file, e.g., myapp/context_processors.py

from django.utils import timezone


def trial_status(request):
    if request.user.is_authenticated:
        # Assuming you have a UserProfile model with a trial_end_date field
        customer = request.user.djstripe_customers.first()
        if not customer:
            return {"is_trial": False, "trial_days_left": 0}
        subscription = customer.subscriptions.first()
        if not subscription:
            return {"is_trial": False, "trial_days_left": 0}

        if subscription.status == "trialing":
            trial_end_date = subscription.trial_end
            days_left = (trial_end_date - timezone.now()).days
            is_trial = days_left > 0
            return {"is_trial": is_trial, "trial_days_left": max(0, days_left)}
    return {"is_trial": False, "trial_days_left": 0}
