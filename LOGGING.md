# MergeCal Logging Strategy

## Overview

This document describes the comprehensive logging strategy implemented across MergeCal. The logging tells the story of what's happening in the application, making it easy to debug issues, monitor performance, and understand user behavior.

## Logging Philosophy

**We log everything meaningful that tells a story:**
- User journeys (registration, calendar creation, source addition)
- System operations (calendar merging, fetching, caching)
- Business events (subscription changes, tier upgrades)
- Performance metrics (duration, size, cache hit/miss)
- Error states and failures
- Security events (authentication, authorization failures)

**Don't worry about over-logging** - storage is cheap, debugging without logs is expensive.

## Log Levels

### DEBUG
- Detailed diagnostic information
- URL validation steps
- Cache operations
- Internal state changes

### INFO
- User actions (login, logout, calendar creation)
- Successful operations (calendar merge, source fetch)
- Business events (subscription changes)
- Performance metrics
- Cache hit/miss ratios

### WARNING
- Business rule violations (tier limits)
- Permission denials
- Degraded operations (timezone conversion failures)
- Deprecated domain usage

### ERROR
- Operation failures (network errors, validation errors)
- Exception conditions
- Data integrity issues

### CRITICAL
- System-wide failures
- Data corruption
- Security breaches

## Logging Structure

All logs follow a consistent pattern:
```
{category}: {action} - {key_details}
```

Examples:
```
Calendar merge: Starting - calendar=My Calendar, uuid=abc123, owner=john, tier=business
Calendar fetch: Cache HIT - url=https://example.com/cal.ics, size=12345 bytes
Auth: User login - username=john, email=john@example.com, tier=free, ip=192.168.1.1
```

## What We Log

### 1. Authentication & Authorization

**Login/Logout (users/adapters.py)**
```python
logger.info("Auth: User login - username=%s, email=%s, tier=%s, ip=%s", ...)
logger.info("Auth: User logout - username=%s, ip=%s", ...)
```

**Social Authentication (users/adapters.py)**
```python
logger.info("Auth: Social login attempt - provider=%s, email=%s, ip=%s", ...)
logger.info("Auth: New social user created - provider=%s, username=%s, email=%s", ...)
```

**Permission Denials (calendars/models.py)**
```python
logger.warning("Calendar validation failed: User %s (tier=%s) attempted to set custom update frequency", ...)
logger.warning("Source customization denied: User %s (tier=%s) attempted to use premium features", ...)
```

### 2. Calendar Operations

**Calendar Creation/Update/Delete (calendars/views.py)**
```python
logger.info("User %s created a new calendar %s", user, calendar)
logger.info("User %s updated the calendar %s", user, calendar)
logger.info("User %s deleted the calendar %s", user, calendar)
```

**Calendar Merge Process (calendars/services/calendar_merger_service.py)**
```python
logger.info("Calendar merge: Starting - calendar=%s, uuid=%s, owner=%s, tier=%s", ...)
logger.info("Calendar merge: Cache HIT - calendar=%s, uuid=%s, size=%d bytes", ...)
logger.info("Calendar merge: Sources processed - total=%d, successful=%d, failed=%d", ...)
logger.info("Calendar merge: SUCCESS - size=%d bytes, duration=%.2fs, cache_ttl=%ds", ...)
```

**Calendar Access (calendars/views.py)**
```python
logger.info("Calendar access: Request received - uuid=%s, method=%s, user_agent=%s, ip=%s", ...)
logger.info("Calendar access: SUCCESS - uuid=%s, size=%d bytes, duration=%.2fs", ...)
```

### 3. Source Operations

**Source Fetching (calendars/calendar_fetcher.py)**
```python
logger.info("Calendar fetch: Cache MISS - fetching from remote url=%s", ...)
logger.info("Calendar fetch: SUCCESS - url=%s, status=%d, size=%d bytes, duration=%.2fs", ...)
logger.error("Calendar fetch: FAILED - url=%s, error=%s, error_type=%s, duration=%.2fs", ...)
```

**Source Processing (calendars/services/source_processor.py)**
```python
logger.info("Source fetch: SUCCESS - source=%s, url=%s", ...)
logger.error("Source fetch: FAILED (network error) - source=%s, url=%s, error=%s", ...)
```

**Source Customization (calendars/services/source_processor.py)**
```python
logger.info("Source customization: Complete - source=%s, events_removed=%d, events_customized=%d", ...)
```

### 4. Validation & Business Rules

**URL Validation (calendars/models.py)**
```python
logger.debug("Validating iCal URL: %s", url)
logger.info("iCal URL validation successful: %s", url)
logger.error("iCal URL validation failed (network error): url=%s, error=%s", ...)
```

**Tier Limits (calendars/models.py)**
```python
logger.warning("Calendar creation denied: User %s (tier=%s) at limit - current=%d", ...)
logger.warning("Source creation denied: Calendar '%s' (owner=%s, tier=%s) at limit - current=%d", ...)
```

### 5. Cache Operations

**Cache Invalidation (calendars/signals.py)**
```python
logger.info("Signal: Source created - source=%s, url=%s, calendar=%s, owner=%s", ...)
logger.info("Cache invalidation: Source change - cache_key=%s, source=%s, action=%s", ...)
```

**Cache Hit/Miss (calendars/calendar_fetcher.py, calendars/services/calendar_merger_service.py)**
```python
logger.info("Calendar fetch: Cache HIT - url=%s, size=%d bytes", ...)
logger.info("Calendar merge: Cache MISS - generating calendar - calendar=%s", ...)
```

### 6. Billing & Subscriptions

**Subscription Events (billing/signals.py)**
```python
logger.info("User %s has been updated to %s tier", user, new_tier)
logger.info("Subscription trial will end soon for customer: %s", customer)
logger.info("Subscription ended for customer: %s", customer)
```

**Payment Events (billing/signals.py)**
```python
logger.info("Invoice paid for user: %s", user)
logger.info("Invoice payment failed for user: %s", user)
logger.info("Payment method attached for user: %s", user)
```

**Webhook Events (billing/signals.py)**
```python
logger.info("Webhook Event Type: %s", event.type)
logger.info("Checkout session completed for customer: %s", customer)
```

### 7. Celery Tasks

**Background Jobs (calendars/tasks.py)**
```python
task_logger.info("Celery task: Starting calendar combine - calendar_id=%s", cal_id)
task_logger.info("Celery task: Calendar combine SUCCESS - calendar_id=%s, duration=%.2fs", ...)
task_logger.error("Celery task: Calendar combine FAILED - calendar_id=%s, error=%s", ...)
```

**Billing Tasks (billing/tasks.py)**
```python
logger.info("Triggered update for user %s associated with Stripe customer %s", ...)
logger.exception("Error processing Stripe customer %s", customer.id)
```

### 8. Performance Metrics

Every long-running operation logs:
- Start time
- Duration
- Size (bytes)
- Success/failure status

Example:
```python
start_time = time.time()
# ... operation ...
duration = time.time() - start_time
logger.info("Operation: SUCCESS - duration=%.2fs, size=%d bytes", duration, size)
```

## Configuration

### Production Settings (config/settings/production.py)

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(name)s.%(funcName)s:%(lineno)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "sentry_sdk": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
```

### Sentry Integration

Sentry captures:
- ERROR and above as events
- INFO and above as breadcrumbs
- Payment method attachments as info messages
- User context for all events

## Log Analysis Patterns

### Debugging Calendar Issues

1. **Find calendar access:**
   ```
   grep "Calendar access: Request received" | grep "uuid=abc123"
   ```

2. **Trace merge process:**
   ```
   grep "Calendar merge:" | grep "calendar=My Calendar"
   ```

3. **Check source failures:**
   ```
   grep "Source fetch: FAILED" | grep "source=Work Calendar"
   ```

### Performance Analysis

1. **Slow operations:**
   ```
   grep "duration=" | awk -F'duration=' '{print $2}' | sort -n
   ```

2. **Cache efficiency:**
   ```
   grep "Cache HIT" | wc -l
   grep "Cache MISS" | wc -l
   ```

3. **Large responses:**
   ```
   grep "size=" | awk -F'size=' '{print $2}' | sort -n
   ```

### User Journey Tracking

1. **User signup to first calendar:**
   ```
   grep "Auth: New social user created.*username=john"
   grep "User john created a new calendar"
   grep "User john added a new source"
   ```

2. **Subscription changes:**
   ```
   grep "User john.*tier" | grep -E "(updated to|attempted)"
   ```

### Security Monitoring

1. **Failed login attempts:**
   ```
   grep "Auth: User login" | grep -v "SUCCESS"
   ```

2. **Permission denials:**
   ```
   grep "denied:" | grep "User john"
   ```

3. **Suspicious access patterns:**
   ```
   grep "Calendar access:" | awk '{print $NF}' | sort | uniq -c | sort -rn
   ```

## Best Practices

### DO:
✅ Log user actions with context (user, tier, resource)
✅ Log performance metrics (duration, size)
✅ Log error details (error type, message, context)
✅ Use structured logging with key=value pairs
✅ Include correlation IDs when available
✅ Log both success and failure paths
✅ Use appropriate log levels
✅ Log security-relevant events

### DON'T:
❌ Log sensitive data (passwords, tokens, API keys)
❌ Log full credit card numbers
❌ Log personally identifiable info without sanitization
❌ Create logs without context
❌ Use print() or console.log()
❌ Log in tight loops without throttling
❌ Ignore exceptions silently

## Logger Naming Convention

Follow Python's module-based logger naming:

```python
import logging

logger = logging.getLogger(__name__)  # Uses module path, e.g., 'mergecalweb.calendars.models'
```

For Celery tasks:
```python
from celery.utils.log import get_task_logger

task_logger = get_task_logger(__name__)  # Integrates with Celery's logging
```

## Adding New Logs

When adding logging to new code:

1. **Import the logger at module level:**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

2. **Use the category: action pattern:**
   ```python
   logger.info("Category: Action - key1=%s, key2=%s", value1, value2)
   ```

3. **Log both paths:**
   ```python
   try:
       result = operation()
       logger.info("Operation: SUCCESS - details=%s", details)
   except Exception as e:
       logger.error("Operation: FAILED - error=%s", str(e))
       raise
   ```

4. **Include performance metrics for expensive operations:**
   ```python
   import time
   start = time.time()
   result = expensive_operation()
   logger.info("Operation: Complete - duration=%.2fs", time.time() - start)
   ```

## Monitoring & Alerting

### Key Metrics to Monitor

1. **Error Rate:**
   - `ERROR` and `CRITICAL` log count
   - Alert if >1% of requests fail

2. **Performance:**
   - Average calendar merge duration
   - 95th percentile fetch time
   - Alert if >5s for p95

3. **Business Metrics:**
   - Calendar access rate
   - Source fetch failures
   - Subscription changes
   - Cache hit ratio (should be >80%)

4. **Security:**
   - Failed login attempts per IP
   - Permission denial rate
   - Unusual access patterns

### Setting Up Alerts

Use your log aggregation tool (e.g., CloudWatch, Datadog, ELK) to create alerts:

1. **High error rate:**
   ```
   count(level=ERROR) > 100 in 5 minutes
   ```

2. **Slow operations:**
   ```
   avg(duration) > 5.0 in 10 minutes where operation="Calendar merge"
   ```

3. **Low cache hit rate:**
   ```
   (cache_hits / total_fetches) < 0.8 in 1 hour
   ```

4. **Subscription issues:**
   ```
   count("Invoice payment failed") > 10 in 1 hour
   ```

## Log Retention

- **Development:** 7 days
- **Production:** 90 days
- **Critical security logs:** 1 year
- **Compliance logs:** As per legal requirements

## Conclusion

This comprehensive logging strategy ensures that MergeCal tells its story through logs. Every meaningful operation, user action, and system event is captured with enough context to understand what happened, why it happened, and how long it took.

When debugging issues, start with the logs - they contain the answers.
