"""
Logging event constants for structured logging.

All log events use the `extra` parameter with an "event" field.
These constants ensure consistency across the codebase.

Usage:
    logger.info(
        "Human readable message",
        extra={
            "event": LogEvent.USER_LOGIN,
            "user_id": user.pk,
            ...
        }
    )
"""


class LogEvent:
    """Logging event type constants for structured logging."""

    # Billing - Subscription Management
    SUBSCRIPTION_TIER_CHANGE = "subscription-tier-change"
    SUBSCRIPTION_UPDATE = "subscription-update"
    SUBSCRIPTION_ENDED = "subscription-ended"

    # Billing - Customer Management
    STRIPE_CUSTOMER_CREATED = "stripe-customer-created"
    STRIPE_CUSTOMER_ATTACHED = "stripe-customer-attached"

    # Billing - Trial Events
    TRIAL_ENDING = "trial-ending"
    TRIAL_ENDING_NO_USER = "trial-ending-no-user"

    # Billing - Checkout & Payment
    CHECKOUT_COMPLETED = "checkout-completed"
    CHECKOUT_SESSION_RETRIEVED = "checkout-session-retrieved"
    CHECKOUT_SUCCESS_PAGE_VIEW = "checkout-success-page-view"
    PAYMENT_METHOD_ATTACHED = "payment-method-attached"

    # Billing - Invoice Events
    INVOICE_PAID = "invoice-paid"
    INVOICE_PAYMENT_FAILED = "invoice-payment-failed"
    INVOICE_EVENT = "invoice-event"

    # Billing - Views
    PRICING_TABLE_VIEW = "pricing-table-view"
    BILLING_PORTAL_ACCESS = "billing-portal-access"

    # Billing - Errors (no user/customer)
    SUBSCRIPTION_UPDATE_NO_USER = "subscription-update-no-user"
    SUBSCRIPTION_END_NO_USER = "subscription-end-no-user"
    INVOICE_EVENT_NO_USER = "invoice-event-no-user"
    PAYMENT_METHOD_NO_CUSTOMER = "payment-method-no-customer"
    PAYMENT_METHOD_NO_USER = "payment-method-no-user"
    SUBSCRIPTION_UPDATE_NO_CUSTOMER = "subscription-update-no-customer"
    SUBSCRIPTION_UPDATE_NO_SUBSCRIPTION = "subscription-update-no-subscription"

    # Billing - Background Tasks
    SUBSCRIPTION_UPDATE_TASK = "subscription-update-task"
    BULK_SUBSCRIPTION_SYNC_START = "bulk-subscription-sync-start"
    BULK_SUBSCRIPTION_SYNC_COMPLETE = "bulk-subscription-sync-complete"
    SUBSCRIPTION_SYNC_QUEUED = "subscription-sync-queued"
    SUBSCRIPTION_SYNC_ERROR = "subscription-sync-error"
    SUBSCRIPTION_SYNC_INVALID_SUBSCRIBER = "subscription-sync-invalid-subscriber"

    # User Profile
    USER_PROFILE_VIEW = "user-profile-view"
    USER_PROFILE_UPDATED = "user-profile-updated"
    USER_PROFILE_SUBSCRIPTION_SYNC = "user-profile-subscription-sync"

    # Calendar CRUD Operations
    CALENDAR_CREATED = "calendar-created"
    CALENDAR_UPDATED = "calendar-updated"
    CALENDAR_DELETED = "calendar-deleted"

    # Source CRUD Operations
    SOURCE_ADDED = "source-added"
    SOURCE_UPDATED = "source-updated"
    SOURCE_DELETED = "source-deleted"

    # Calendar Access (external calendar clients fetching .ics files)
    CALENDAR_FILE_ACCESS = "calendar-file-access"
    CALENDAR_FILE_SUCCESS = "calendar-file-success"
    CALENDAR_FILE_MERGE_FAILED = "calendar-file-merge-failed"

    # Calendar Web Views (human viewing pages)
    CALENDAR_WEB_VIEW = "calendar-web-view"
    CALENDAR_IFRAME_VIEW = "calendar-iframe-view"

    # Staff Tools
    URL_VALIDATOR_ACCESS = "url-validator-access"

    # Calendar Fetching (external source fetching)
    CALENDAR_FETCH_CACHE_HIT = "calendar-fetch-cache-hit"
    CALENDAR_FETCH_CACHE_MISS = "calendar-fetch-cache-miss"
    CALENDAR_FETCH_SUCCESS = "calendar-fetch-success"
    CALENDAR_FETCH_CACHED = "calendar-fetch-cached"
    CALENDAR_FETCH_FAILED = "calendar-fetch-failed"

    # Calendar Merging
    CALENDAR_MERGE_START = "calendar-merge-start"
    CALENDAR_MERGE_FREE_TIER_WARNING = "calendar-merge-free-tier-warning"
    CALENDAR_MERGE_CACHE_HIT = "calendar-merge-cache-hit"
    CALENDAR_MERGE_CACHE_MISS = "calendar-merge-cache-miss"
    CALENDAR_SOURCES_PROCESSED = "calendar-sources-processed"
    CALENDAR_MERGE_SUCCESS = "calendar-merge-success"

    # Source Processing
    SOURCE_FETCH_START = "source-fetch-start"
    SOURCE_FETCH_SUCCESS = "source-fetch-success"
    SOURCE_FETCH_NETWORK_ERROR = "source-fetch-network-error"
    SOURCE_FETCH_VALIDATION_ERROR = "source-fetch-validation-error"
    SOURCE_TIMEZONE_STANDARDIZED = "source-timezone-standardized"
    SOURCE_TIMEZONE_SKIP = "source-timezone-skip"

    # Source Customization (business tier features)
    SOURCE_CUSTOMIZATION_START = "source-customization-start"
    SOURCE_CUSTOMIZATION_SKIPPED = "source-customization-skipped"
    SOURCE_CUSTOMIZATION_COMPLETE = "source-customization-complete"

    # Calendar Background Tasks
    BULK_CALENDAR_COMBINE_START = "bulk-calendar-combine-start"
    BULK_CALENDAR_COMBINE_QUEUED = "bulk-calendar-combine-queued"
    CALENDAR_COMBINE_TASK_START = "calendar-combine-task-start"
    CALENDAR_COMBINE_LOADED = "calendar-combine-loaded"
    CALENDAR_COMBINE_TASK_SUCCESS = "calendar-combine-task-success"
    CALENDAR_COMBINE_TASK_NOT_FOUND = "calendar-combine-task-not-found"
    CALENDAR_COMBINE_TASK_ERROR = "calendar-combine-task-error"
