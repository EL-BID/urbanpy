"""Shared provider-friendly HTTP defaults for UrbanPy clients."""

from __future__ import annotations

from typing import Any, Final

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT: Final = (5.0, 60.0)
DEFAULT_USER_AGENT: Final = (
    "urbanpy/0.3 (+https://github.com/EL-BID/urbanpy; "
    "https://github.com/EL-BID/urbanpy/blob/master/SUPPORT.md)"
)


class UrbanPySession(requests.Session):
    """Requests session that cannot accidentally omit a finite timeout."""

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return super().request(method, url, **kwargs)


def build_session() -> UrbanPySession:
    session = UrbanPySession()
    session.headers.update(
        {"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT}
    )
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        status=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD", "OPTIONS"),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=32)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


__all__ = ["DEFAULT_TIMEOUT", "DEFAULT_USER_AGENT", "UrbanPySession", "build_session"]
