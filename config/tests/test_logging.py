# ruff: noqa: PLR2004
from __future__ import annotations

import logging
from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory  # noqa: TC002

from config.request_logging import RequestContextFilter
from config.request_logging import RequestContextMiddleware
from config.request_logging import ip_address_var
from config.request_logging import request_id_var
from config.request_logging import request_method_var
from config.request_logging import request_path_var
from config.request_logging import session_id_var
from config.request_logging import user_email_var
from config.request_logging import user_id_var
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestRequestContextFilter:
    def test_filter_adds_context_fields_to_log_record(self):
        """Filter should add all context fields to log records."""
        # Set context variables
        request_id_var.set("test-request-id")
        session_id_var.set("test-session-id")
        user_id_var.set(123)
        user_email_var.set("test@example.com")
        request_path_var.set("/test/path/")
        request_method_var.set("GET")
        ip_address_var.set("192.168.1.1")

        filter_instance = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True
        assert record.request_id == "test-request-id"
        assert record.session_id == "test-session-id"
        assert record.user_id == 123
        assert record.user_email == "test@example.com"
        assert record.request_path == "/test/path/"
        assert record.request_method == "GET"
        assert record.ip_address == "192.168.1.1"

    def test_filter_adds_none_when_context_not_set(self):
        """Filter should add None values when context vars are not set."""
        # Reset all context variables
        request_id_var.set(None)
        session_id_var.set(None)
        user_id_var.set(None)
        user_email_var.set(None)
        request_path_var.set(None)
        request_method_var.set(None)
        ip_address_var.set(None)

        filter_instance = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True
        assert record.request_id is None
        assert record.session_id is None
        assert record.user_id is None
        assert record.user_email is None
        assert record.request_path is None
        assert record.request_method is None
        assert record.ip_address is None


class TestRequestContextMiddleware:
    def test_middleware_sets_request_context_for_authenticated_user(
        self,
        rf: RequestFactory,
    ):
        """Middleware should set all context vars for authenticated users."""
        user = UserFactory()
        request = rf.get("/test/path/")
        request.user = user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        captured_context = {}

        def get_response(req):
            captured_context["request_id"] = request_id_var.get()
            captured_context["session_id"] = session_id_var.get()
            captured_context["user_id"] = user_id_var.get()
            captured_context["user_email"] = user_email_var.get()
            captured_context["request_path"] = request_path_var.get()
            captured_context["request_method"] = request_method_var.get()
            captured_context["ip_address"] = ip_address_var.get()
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request)

        assert captured_context["request_id"] is not None
        assert len(captured_context["request_id"]) == 36  # UUID format
        assert captured_context["session_id"] == "test-session-key"
        assert captured_context["user_id"] == user.pk
        assert captured_context["user_email"] == user.email
        assert captured_context["request_path"] == "/test/path/"
        assert captured_context["request_method"] == "GET"
        assert captured_context["ip_address"] == "192.168.1.100"

    def test_middleware_handles_anonymous_user(self, rf: RequestFactory):
        """Middleware should handle anonymous users without user_id/email."""
        request = rf.get("/public/page/")
        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = None
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        captured_context = {}

        def get_response(req):
            captured_context["request_id"] = request_id_var.get()
            captured_context["session_id"] = session_id_var.get()
            captured_context["user_id"] = user_id_var.get()
            captured_context["user_email"] = user_email_var.get()
            captured_context["request_path"] = request_path_var.get()
            captured_context["request_method"] = request_method_var.get()
            captured_context["ip_address"] = ip_address_var.get()
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request)

        assert captured_context["request_id"] is not None
        assert captured_context["session_id"] is None
        assert captured_context["user_id"] is None
        assert captured_context["user_email"] is None
        assert captured_context["request_path"] == "/public/page/"
        assert captured_context["request_method"] == "GET"
        assert captured_context["ip_address"] == "10.0.0.1"

    def test_middleware_extracts_ip_from_x_forwarded_for(self, rf: RequestFactory):
        """Middleware should extract client IP from X-Forwarded-For header."""
        request = rf.get("/test/")
        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = None
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.50, 70.41.3.18"
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        captured_ip = None

        def get_response(req):
            nonlocal captured_ip
            captured_ip = ip_address_var.get()
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request)

        assert captured_ip == "203.0.113.50"

    def test_middleware_resets_context_after_request(self, rf: RequestFactory):
        """Middleware should reset context vars after processing the request."""
        request = rf.get("/test/")
        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = "some-session"
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        def get_response(req):
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request)

        # After request, all context vars should be reset
        assert request_id_var.get() is None
        assert session_id_var.get() is None
        assert user_id_var.get() is None
        assert user_email_var.get() is None
        assert request_path_var.set is not None
        assert request_method_var.get() is None
        assert ip_address_var.get() is None

    def test_middleware_handles_post_request(self, rf: RequestFactory):
        """Middleware should correctly capture POST request method."""
        request = rf.post("/submit/form/")
        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = None
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        captured_method = None

        def get_response(req):
            nonlocal captured_method
            captured_method = request_method_var.get()
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request)

        assert captured_method == "POST"

    def test_middleware_generates_unique_request_ids(self, rf: RequestFactory):
        """Each request should get a unique request ID."""
        request1 = rf.get("/test1/")
        request1.user = AnonymousUser()
        request1.session = MagicMock()
        request1.session.session_key = None
        request1.META["REMOTE_ADDR"] = "10.0.0.1"

        request2 = rf.get("/test2/")
        request2.user = AnonymousUser()
        request2.session = MagicMock()
        request2.session.session_key = None
        request2.META["REMOTE_ADDR"] = "10.0.0.1"

        request_ids = []

        def get_response(req):
            request_ids.append(request_id_var.get())
            return Mock()

        middleware = RequestContextMiddleware(get_response)
        middleware(request1)
        middleware(request2)

        assert len(request_ids) == 2
        assert request_ids[0] != request_ids[1]
