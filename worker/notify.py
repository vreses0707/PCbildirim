"""Bildirim kanalları: console (dry-run) ve Telegram."""
from __future__ import annotations

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


class ConsoleNotifier:
    """Bildirimleri ekrana yazar — hesap/secret gerektirmez, lokal test için."""

    def send(self, text: str) -> bool:
        print("\n┌─ BİLDİRİM ─────────────────────────")
        for line in text.splitlines():
            print("│ " + line)
        print("└────────────────────────────────────")
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
