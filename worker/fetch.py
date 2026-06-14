"""Basit, nazik HTTP istemcisi: gerçekçi User-Agent, retry ve istekler arası bekleme."""
from __future__ import annotations

import time

import requests

from .config import REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            }
        )
        _session = s
    return _session


def get(url: str, retries: int = 2) -> requests.Response:
    """URL'i çeker. Hata olursa kısa beklemeyle birkaç kez dener. Her çağrıdan
    sonra siteyi yormamak için REQUEST_DELAY kadar bekler."""
    s = _get_session()
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = s.get(url, timeout=REQUEST_TIMEOUT)
            time.sleep(REQUEST_DELAY)
            return resp
        except requests.RequestException as exc:  # ağ hatası -> tekrar dene
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]
