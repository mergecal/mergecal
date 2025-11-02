"""
Logging event constants for structured logging.

All log events use the `extra` parameter with an "event" field.
These constants ensure consistency across the codebase.

Usage:
    logger.info(
        "Human readable message",
        extra={
            "event": LogEvent.USER_ACTION,
            "action": "login",
            "user_id": user.pk,
            ...
        }
    )

Many events use additional parameters for specificity:
    - "action": Specific action type (e.g., "login", "logout",
                "created", "updated", "deleted")
    - "error_type": Type of error (e.g., "network", "timeout",
                    "validation")
    - "status": Status indicator (e.g., "success", "failed", "denied")
"""


class LogEvent:
    """Logging event type constants for structured logging."""

    # Billing - Core Events
    SUBSCRIPTION_TIER_CHANGE = "subscription-tier-change"
    SUBSCRIPTION_UPDATE = "subscription-update"
    SUBSCRIPTION_ENDED = "subscription-ended"
    STRIPE_CUSTOMER_CREATED = "stripe-customer-created"
    STRIPE_CUSTOMER_ATTACHED = "stripe-customer-attached"
    TRIAL_ENDING = "trial-ending"
    CHECKOUT_COMPLETED = "checkout-completed"
    CHECKOUT_SESSION_RETRIEVED = "checkout-session-retrieved"
    PAYMENT_METHOD_ATTACHED = "payment-method-attached"
    INVOICE_EVENT = "invoice-event"  # Use with "invoice_type": "paid"/"failed"

    # Billing - Errors (use with "error_type" parameter)
    # Use with "error_type": "no-user"/"no-customer"/"no-subscription"
    BILLING_ERROR = "billing-error"

    # Billing - Background Tasks
    # Use with "status": "start"/"queued"/"complete"/"error"
    SUBSCRIPTION_SYNC = "subscription-sync"

    # Views (use with "view_type" parameter)
    # "pricing"/"billing-portal"/"profile"/"blog-list"/"blog-detail"/
    # "calendar-web"/"calendar-iframe"/"url-validator"
    PAGE_VIEW = "page-view"

    # User Actions
    USER_PROFILE_UPDATED = "user-profile-updated"

    # Calendar CRUD (use with "action" parameter)
    # Use with "action": "created"/"updated"/"deleted"
    CALENDAR_ACTION = "calendar-action"

    # Source CRUD (use with "action" parameter)
    # Use with "action": "added"/"updated"/"deleted"
    SOURCE_ACTION = "source-action"

    # Validation Events (use with "validation_type" and "status" parameters)
    # "validation_type": "ical-url"/"calendar-limit"/"source-limit"/
    # "tier-feature", "status": "success"/"failed"/"denied"
    VALIDATION = "validation"

    # Calendar File Access (external .ics file requests)
    CALENDAR_FILE_ACCESS = "calendar-file-access"
    CALENDAR_FILE_SUCCESS = "calendar-file-success"
    CALENDAR_FILE_ERROR = "calendar-file-error"

    # Calendar Fetching (external source fetching - use with "status" parameter)
    # Use with "status": "cache-hit"/"cache-miss"/"success"/"failed"/
    # "domain-config"
    CALENDAR_FETCH = "calendar-fetch"

    # Calendar Merging (use with "status" parameter)
    # Use with "status": "start"/"cache-hit"/"cache-miss"/
    # "sources-processed"/"success"/"free-tier-warning"
    CALENDAR_MERGE = "calendar-merge"

    # Source Processing (use with "status" and optionally "source_type")
    # Use with "status": "start"/"success"/"timeout"/"network-error"/
    # "validation-error"/"meetup-error"
    # Optionally "source_type": "remote"/"local"/"meetup"
    SOURCE_FETCH = "source-fetch"

    # Source Processing - Errors (use with "error_type")
    # Use with "error_type": "invalid-format"/"circular-ref"/"not-found"
    SOURCE_ERROR = "source-error"

    # Source Timezone & Customization
    # Use with "action": "standardized"/"skipped"
    SOURCE_TIMEZONE = "source-timezone"
    # Use with "status": "start"/"skipped"/"complete"
    SOURCE_CUSTOMIZATION = "source-customization"

    # Calendar Background Tasks (use with "status" parameter)
    # Use with "task_type": "combine"/"bulk-combine"
    # "status": "start"/"queued"/"loaded"/"success"/"not-found"/"error"
    CALENDAR_TASK = "calendar-task"

    # Cache Operations (use with "cache_reason" parameter)
    # Use with "cache_reason": "source-change"/"calendar-change"
    CACHE_INVALIDATED = "cache-invalidated"
