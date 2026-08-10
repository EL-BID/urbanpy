from unittest.mock import Mock

import requests

from urbanpy._http import (
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    UrbanPySession,
    build_session,
)


def test_shared_session_identifies_urbanpy_and_has_retries():
    session = build_session()

    assert session.headers["User-Agent"] == DEFAULT_USER_AGENT
    assert session.headers["Accept"] == "application/json"
    assert session.get_adapter("https://").max_retries.total == 3
    assert "POST" not in session.get_adapter("https://").max_retries.allowed_methods


def test_shared_session_supplies_timeout_without_overriding_explicit_value(monkeypatch):
    request = Mock(return_value=requests.Response())
    monkeypatch.setattr(requests.Session, "request", request)
    session = UrbanPySession()

    session.get("https://example.org")
    assert request.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT

    session.get("https://example.org", timeout=1.5)
    assert request.call_args.kwargs["timeout"] == 1.5
