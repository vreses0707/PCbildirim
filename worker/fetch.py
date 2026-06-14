"""Cloudflare bypass destekli HTTP istemcisi."""
from __future__ import annotations

import time

import cloudscraper

from .config import REQUEST_DELAY, REQUEST_TIMEOUT

_scraper = None


def _get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    return _scraper


def get(url: str, retries: int = 2):
    s = _get_scraper()
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = s.get(url, timeout=REQUEST_TIMEOUT)
            time.sleep(REQUEST_DELAY)
            return resp
        except Exception as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]
