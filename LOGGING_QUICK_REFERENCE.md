# Logging Quick Reference

## Quick Start

### Import and Setup
```python
import logging

logger = logging.getLogger(__name__)

# For Celery tasks:
from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)
```

### Basic Patterns

#### 1. Simple Operation Logging
```python
logger.info("Operation: Action - details=%s", details)
```

#### 2. Success/Failure Logging
```python
try:
    result = operation()
    logger.info("Operation: SUCCESS - result=%s", result)
except Exception as e:
    logger.error("Operation: FAILED - error=%s, type=%s", str(e), type(e).__name__)
    raise
```

#### 3. Performance Logging
```python
import time

start_time = time.time()
result = expensive_operation()
duration = time.time() - start_time

logger.info("Operation: Complete - duration=%.2fs, size=%d", duration, size)
```

#### 4. Validation Logging
```python
logger.debug("Validating input: %s", input_data)

if not is_valid(input_data):
    logger.warning("Validation failed: reason=%s, input=%s", reason, input_data)
    raise ValidationError("Invalid input")

logger.debug("Validation successful")
```

## Log Categories

Use these prefixes for consistency:

- **Auth:** - Authentication/authorization events
- **Calendar merge:** - Calendar merging operations
- **Calendar fetch:** - Fetching calendar data
- **Calendar access:** - User accessing calendars
- **Source fetch:** - Fetching source data
- **Source customization:** - Customizing source events
- **Cache invalidation:** - Cache operations
- **Signal:** - Django signal handling
- **Celery task:** - Background tasks
- **User profile:** - User profile operations
- **Billing:** - Payment and subscription events

## When to Use Each Level

### DEBUG
```python
logger.debug("Cache key: %s", cache_key)
logger.debug("Validating URL: %s", url)
logger.debug("Internal state: %s", state)
```

### INFO
```python
logger.info("User %s created calendar %s", user, calendar)
logger.info("Cache HIT - size=%d bytes", size)
logger.info("Operation: SUCCESS - duration=%.2fs", duration)
```

### WARNING
```python
logger.warning("User %s (tier=%s) at limit - current=%d", user, tier, count)
logger.warning("Permission denied: %s attempted %s", user, action)
logger.warning("Deprecated feature used: %s", feature)
```

### ERROR
```python
logger.error("Operation failed: error=%s, context=%s", error, context)
logger.error("Network error: url=%s, status=%d", url, status)
```

### CRITICAL
```python
logger.critical("System failure: %s", details)
logger.critical("Data corruption detected: %s", details)
```

## Common Logging Scenarios

### 1. User Action
```python
logger.info(
    "User action: %s - user=%s, resource=%s, tier=%s",
    action,
    user.username,
    resource,
    user.subscription_tier,
)
```

### 2. HTTP Request
```python
logger.info(
    "Request: method=%s, path=%s, ip=%s, user_agent=%s",
    request.method,
    request.path,
    request.META.get("REMOTE_ADDR"),
    request.META.get("HTTP_USER_AGENT", "")[:100],
)
```

### 3. Database Operation
```python
logger.debug("Query: model=%s, filters=%s", model, filters)
result = Model.objects.filter(**filters)
logger.info("Query result: model=%s, count=%d", model, result.count())
```

### 4. External API Call
```python
logger.info("API call: url=%s, method=%s", url, method)
start = time.time()

try:
    response = requests.get(url, timeout=30)
    duration = time.time() - start
    logger.info(
        "API call: SUCCESS - url=%s, status=%d, duration=%.2fs",
        url,
        response.status_code,
        duration,
    )
except Exception as e:
    duration = time.time() - start
    logger.error(
        "API call: FAILED - url=%s, error=%s, duration=%.2fs",
        url,
        str(e),
        duration,
    )
    raise
```

### 5. Cache Operations
```python
cache_key = f"prefix_{identifier}"
cached = cache.get(cache_key)

if cached:
    logger.info("Cache HIT - key=%s, size=%d", cache_key, len(cached))
    return cached

logger.info("Cache MISS - key=%s, fetching...", cache_key)
data = fetch_data()
cache.set(cache_key, data, timeout)
logger.debug("Cache SET - key=%s, ttl=%d", cache_key, timeout)
```

### 6. Permission Check
```python
logger.debug("Permission check: user=%s, action=%s", user, action)

if not user.has_permission(action):
    logger.warning(
        "Permission denied: user=%s (tier=%s), action=%s",
        user.username,
        user.subscription_tier,
        action,
    )
    raise PermissionDenied()

logger.debug("Permission granted: user=%s, action=%s", user, action)
```

### 7. Celery Task
```python
@shared_task
def my_task(resource_id):
    import time
    start = time.time()

    task_logger.info("Task start: resource_id=%s", resource_id)

    try:
        result = process_resource(resource_id)
        duration = time.time() - start
        task_logger.info(
            "Task SUCCESS: resource_id=%s, duration=%.2fs",
            resource_id,
            duration,
        )
        return result
    except Exception as e:
        duration = time.time() - start
        task_logger.error(
            "Task FAILED: resource_id=%s, error=%s, duration=%.2fs",
            resource_id,
            str(e),
            duration,
        )
        raise
```

### 8. Signal Handler
```python
@receiver(post_save, sender=MyModel)
def my_signal_handler(sender, instance, created, **kwargs):
    action = "created" if created else "updated"

    logger.info(
        "Signal: Model %s - id=%s, name=%s, user=%s",
        action,
        instance.id,
        instance.name,
        instance.user.username,
    )

    # Do something...

    logger.debug("Signal: Processing complete - id=%s", instance.id)
```

## Context to Include

### Always Include:
- User identifier (username, email, ID)
- Resource identifier (name, UUID, ID)
- Action being performed
- Result (success/failure)

### Often Include:
- User's subscription tier
- Duration (for expensive operations)
- Size (in bytes for data operations)
- IP address (for security-relevant events)
- Error details (type, message)

### Sometimes Include:
- User agent (for HTTP requests)
- Referer (for tracking sources)
- Cache keys
- Query parameters
- Request method

## Don't Log These:

❌ **Never log:**
- Passwords (plain or hashed)
- API keys, tokens, secrets
- Full credit card numbers
- Social Security Numbers
- Other PII without sanitization

❌ **Avoid logging:**
- Full request/response bodies (log summary instead)
- Entire stack traces (use logger.exception() instead)
- Sensitive customer data
- Internal system paths in production

## Structured Logging Examples

### Good Examples ✅

```python
# Rich context
logger.info(
    "Calendar merge: SUCCESS - calendar=%s, uuid=%s, owner=%s, tier=%s, size=%d, duration=%.2fs",
    calendar.name,
    calendar.uuid,
    calendar.owner.username,
    calendar.owner.subscription_tier,
    len(result),
    duration,
)

# Clear failure with context
logger.error(
    "Source fetch: FAILED - source=%s, url=%s, error=%s, error_type=%s, duration=%.2fs",
    source.name,
    source.url,
    str(e),
    type(e).__name__,
    duration,
)

# Business metric
logger.info(
    "User action: Tier limit reached - user=%s, tier=%s, resource=%s, current=%d, limit=%d",
    user.username,
    user.subscription_tier,
    resource_type,
    current_count,
    limit,
)
```

### Bad Examples ❌

```python
# Too vague
logger.info("Operation completed")

# Missing context
logger.error("Error occurred: %s", str(e))

# Too verbose
logger.info("User %s with email %s and tier %s performed action %s on resource %s at %s", ...)

# Using print
print(f"Debug: {value}")  # Never do this!
```

## Testing Your Logs

```python
import logging
from unittest.mock import patch

def test_operation_logging():
    with patch('myapp.module.logger') as mock_logger:
        # Perform operation
        result = my_operation()

        # Verify logging
        mock_logger.info.assert_called_once_with(
            "Operation: SUCCESS - result=%s",
            result,
        )
```

## Log Analysis Commands

```bash
# Find specific operation
grep "Calendar merge:" app.log | grep "uuid=abc-123"

# Count errors
grep "ERROR" app.log | wc -l

# Performance analysis
grep "duration=" app.log | awk -F'duration=' '{print $2}' | awk -F's' '{print $1}' | sort -n

# Cache efficiency
echo "Hits: $(grep 'Cache HIT' app.log | wc -l)"
echo "Misses: $(grep 'Cache MISS' app.log | wc -l)"

# Top error types
grep "ERROR" app.log | awk -F'error_type=' '{print $2}' | awk '{print $1}' | sort | uniq -c | sort -rn

# User activity
grep "user=john" app.log | grep "INFO"

# Failed logins
grep "Auth:" app.log | grep -i "fail"

# Slow operations (>5s)
grep "duration=" app.log | awk -F'duration=' '{if ($2 > 5) print $0}'
```

## Quick Checklist

Before committing code with logging:

- [ ] Imported logger correctly
- [ ] Used appropriate log level
- [ ] Included relevant context (user, resource, action)
- [ ] Logged both success and failure paths
- [ ] Added performance metrics for expensive operations
- [ ] Used structured format (key=value pairs)
- [ ] No sensitive data in logs
- [ ] Consistent category prefix
- [ ] Exception details included (but not full tracebacks)
- [ ] Tested locally to verify log output

## Need Help?

See the full documentation:
- `LOGGING.md` - Complete logging strategy and patterns
- `LOGGING_IMPLEMENTATION_SUMMARY.md` - What was implemented and where
