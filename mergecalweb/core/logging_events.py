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
    SUBSCRIPTION_TIER_CHANGE = "subscription_tier_change"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_ENDED = "subscription_ended"

    # Billing - Customer Management
    STRIPE_CUSTOMER_CREATED = "stripe_customer_created"
    STRIPE_CUSTOMER_ATTACHED = "stripe_customer_attached"

    # Billing - Trial Events
    TRIAL_ENDING = "trial_ending"
    TRIAL_ENDING_NO_USER = "trial_ending_no_user"

    # Billing - Checkout & Payment
    CHECKOUT_COMPLETED = "checkout_completed"
    CHECKOUT_SESSION_RETRIEVED = "checkout_session_retrieved"
    CHECKOUT_SUCCESS_PAGE_VIEW = "checkout_success_page_view"
    PAYMENT_METHOD_ATTACHED = "payment_method_attached"

    # Billing - Invoice Events
    INVOICE_PAID = "invoice_paid"
    INVOICE_PAYMENT_FAILED = "invoice_payment_failed"
    INVOICE_EVENT = "invoice_event"

    # Billing - Views
    PRICING_TABLE_VIEW = "pricing_table_view"
    BILLING_PORTAL_ACCESS = "billing_portal_access"

    # Billing - Errors (no user/customer)
    SUBSCRIPTION_UPDATE_NO_USER = "subscription_update_no_user"
    SUBSCRIPTION_END_NO_USER = "subscription_end_no_user"
    INVOICE_EVENT_NO_USER = "invoice_event_no_user"
    PAYMENT_METHOD_NO_CUSTOMER = "payment_method_no_customer"
    PAYMENT_METHOD_NO_USER = "payment_method_no_user"
    SUBSCRIPTION_UPDATE_NO_CUSTOMER = "subscription_update_no_customer"
    SUBSCRIPTION_UPDATE_NO_SUBSCRIPTION = "subscription_update_no_subscription"

    # Billing - Background Tasks
    SUBSCRIPTION_UPDATE_TASK = "subscription_update_task"
    BULK_SUBSCRIPTION_SYNC_START = "bulk_subscription_sync_start"
    BULK_SUBSCRIPTION_SYNC_COMPLETE = "bulk_subscription_sync_complete"
    SUBSCRIPTION_SYNC_QUEUED = "subscription_sync_queued"
    SUBSCRIPTION_SYNC_ERROR = "subscription_sync_error"
    SUBSCRIPTION_SYNC_INVALID_SUBSCRIBER = "subscription_sync_invalid_subscriber"

    # User Profile
    USER_PROFILE_VIEW = "user_profile_view"
    USER_PROFILE_UPDATED = "user_profile_updated"
    USER_PROFILE_SUBSCRIPTION_SYNC = "user_profile_subscription_sync"

    # Calendar CRUD Operations
    CALENDAR_CREATED = "calendar_created"
    CALENDAR_UPDATED = "calendar_updated"
    CALENDAR_DELETED = "calendar_deleted"

    # Source CRUD Operations
    SOURCE_ADDED = "source_added"
    SOURCE_UPDATED = "source_updated"
    SOURCE_DELETED = "source_deleted"

    # Calendar Access (external calendar clients fetching .ics files)
    CALENDAR_FILE_ACCESS = "calendar_file_access"
    CALENDAR_FILE_SUCCESS = "calendar_file_success"
    CALENDAR_FILE_MERGE_FAILED = "calendar_file_merge_failed"

    # Calendar Web Views (human viewing pages)
    CALENDAR_WEB_VIEW = "calendar_web_view"
    CALENDAR_IFRAME_VIEW = "calendar_iframe_view"

    # Staff Tools
    URL_VALIDATOR_ACCESS = "url_validator_access"

    # Calendar Fetching (external source fetching)
    CALENDAR_FETCH_CACHE_HIT = "calendar_fetch_cache_hit"
    CALENDAR_FETCH_CACHE_MISS = "calendar_fetch_cache_miss"
    CALENDAR_FETCH_SUCCESS = "calendar_fetch_success"
    CALENDAR_FETCH_CACHED = "calendar_fetch_cached"
    CALENDAR_FETCH_FAILED = "calendar_fetch_failed"

    # Calendar Merging
    CALENDAR_MERGE_START = "calendar_merge_start"
    CALENDAR_MERGE_FREE_TIER_WARNING = "calendar_merge_free_tier_warning"
    CALENDAR_MERGE_CACHE_HIT = "calendar_merge_cache_hit"
    CALENDAR_MERGE_CACHE_MISS = "calendar_merge_cache_miss"
    CALENDAR_SOURCES_PROCESSED = "calendar_sources_processed"
    CALENDAR_MERGE_SUCCESS = "calendar_merge_success"

    # Source Processing
    SOURCE_FETCH_START = "source_fetch_start"
    SOURCE_FETCH_SUCCESS = "source_fetch_success"
    SOURCE_FETCH_NETWORK_ERROR = "source_fetch_network_error"
    SOURCE_FETCH_VALIDATION_ERROR = "source_fetch_validation_error"
    SOURCE_TIMEZONE_STANDARDIZED = "source_timezone_standardized"
    SOURCE_TIMEZONE_SKIP = "source_timezone_skip"

    # Source Customization (business tier features)
    SOURCE_CUSTOMIZATION_START = "source_customization_start"
    SOURCE_CUSTOMIZATION_SKIPPED = "source_customization_skipped"
    SOURCE_CUSTOMIZATION_COMPLETE = "source_customization_complete"

    # Calendar Background Tasks
    BULK_CALENDAR_COMBINE_START = "bulk_calendar_combine_start"
    BULK_CALENDAR_COMBINE_QUEUED = "bulk_calendar_combine_queued"
    CALENDAR_COMBINE_TASK_START = "calendar_combine_task_start"
    CALENDAR_COMBINE_LOADED = "calendar_combine_loaded"
    CALENDAR_COMBINE_TASK_SUCCESS = "calendar_combine_task_success"
    CALENDAR_COMBINE_TASK_NOT_FOUND = "calendar_combine_task_not_found"
    CALENDAR_COMBINE_TASK_ERROR = "calendar_combine_task_error"
