"""Bildirim kanalları: console (dry-run) ve Telegram."""
from __future__ import annotations

import sys

import requests

from .config import REQUEST_TIMEOUT
from .match import DropEvent
from .pricing import format_price


def format_drop_message(ev: DropEvent, filter_label: str) -> str:
    pct = round(ev.drop_pct)
    p = ev.product
    return (
        f"💸 Fiyat düştü — {p.name}\n"
        f"{format_price(ev.old_price)} → {format_price(ev.new_price)} (-%{pct})\n"
        f"🏬 {p.site}   🔖 {filter_label}\n"
        f"{p.url}"
    )


def format_campaign_message(p) -> str:
    """Bir ürün kampanya/fırsat sayfasında belirince gönderilecek mesaj.
    Eski fiyat varsa indirim yüzdesiyle birlikte gösterir."""
    tag = p.campaign or "Kampanya"
    old = getattr(p, "old_price", None)
    if old and old > p.price:
        pct = round((old - p.price) / old * 100)
        price_line = f"{format_price(old)} → {format_price(p.price)} (-%{pct})"
    else:
        price_line = format_price(p.price)
    return (
        f"🔥 Fırsatta — {p.name}\n"
        f"{price_line}\n"
        f"🏬 {p.site}   🎯 {tag}\n"
        f"{p.url}"
    )


class ConsoleNotifier:
    """Bildirimleri ekrana yazar — hesap/secret gerektirmez, lokal test için."""

    def send(self, text: str) -> bool:
        def _p(s: str) -> None:
            try:
                print(s)
            except UnicodeEncodeError:  # Windows konsolu emoji basamayabilir
                enc = sys.stdout.encoding or "ascii"
                print(s.encode(enc, "replace").decode(enc))

        _p("\n+-- BILDIRIM -------------------------")
        for line in text.splitlines():
            _p("| " + line)
        _p("+------------------------------------")
        return True


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": False,
                },
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                print(f"[telegram] gönderim hatası {resp.status_code}: {resp.text[:200]}")
                return False
            return True
        except requests.RequestException as exc:
            print(f"[telegram] ağ hatası: {exc}")
            return False


def get_notifier(backend: str, *, token: str | None = None, chat_id: str | None = None):
    """backend='telegram' ve gerekli bilgiler varsa Telegram, aksi halde console."""
    if backend == "telegram":
        if token and chat_id:
            return TelegramNotifier(token, chat_id)
        print("[notify] Telegram seçili ama token/chat_id eksik -> console moduna düşülüyor")
    return ConsoleNotifier()
