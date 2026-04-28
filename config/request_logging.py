"""Request context logging utilities.

This module provides automatic request context injection into all log records
using context variables, a logging filter, and Django middleware.

Usage:
    All logs automatically include: request_id, session_id, user_id, user_email,
    request_path, request_method, and ip_address when available.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest
    from django.http import HttpResponse

# Context variables for request-scoped data
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)
user_email_var: ContextVar[str | None] = ContextVar("user_email", default=None)
request_path_var: ContextVar[str | None] = ContextVar("request_path", default=None)
request_method_var: ContextVar[str | None] = ContextVar("request_method", default=None)
ip_address_var: ContextVar[str | None] = ContextVar("ip_address", default=None)


class RequestContextFilter(logging.Filter):
    """Logging filter that adds request context from context variables."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context fields to the log record."""
        record.request_id = request_id_var.get()
        record.session_id = session_id_var.get()
        record.user_id = user_id_var.get()
        record.user_email = user_email_var.get()
        record.request_path = request_path_var.get()
        record.request_method = request_method_var.get()
        record.ip_address = ip_address_var.get()
        return True


class RequestContextMiddleware:
    """Django middleware that populates request context variables."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate unique request ID
        request_id_var.set(str(uuid.uuid4()))

        # Set request info
        request_path_var.set(request.path)
        request_method_var.set(request.method)

        # Get IP address (respects proxy headers)
        ip_address = self._get_client_ip(request)
        ip_address_var.set(ip_address)

        # Session ID - only if session already exists (don't force creation)
        session_key = getattr(request.session, "session_key", None)
        session_id_var.set(session_key)

        # User info - only for authenticated users
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id_var.set(request.user.pk)
            user_email_var.set(getattr(request.user, "email", None))
        else:
            user_id_var.set(None)
            user_email_var.set(None)

        response = self.get_response(request)

        # Reset context vars after request
        self._reset_context()

        return response

    def _get_client_ip(self, request: HttpRequest) -> str | None:
        """Extract client IP from request, respecting X-Forwarded-For header."""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs; first is the client
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _reset_context(self) -> None:
        """Reset all context variables to their defaults."""
        request_id_var.set(None)
        session_id_var.set(None)
        user_id_var.set(None)
        user_email_var.set(None)
        request_path_var.set(None)
        request_method_var.set(None)
        ip_address_var.set(None)
