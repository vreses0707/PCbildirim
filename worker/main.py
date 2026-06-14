"""Orkestrasyon: scrape -> kaydet -> düşüş tespiti -> eşleştir -> bildir.

Çalıştırma:
    python -m worker.main          # bir kez tarar
Ortam:
    STORE=sqlite|supabase   NOTIFY=console|telegram
"""
from __future__ import annotations

from . import config
from .match import detect_drops, filter_matches
from .notify import format_drop_message, get_notifier
from .sites import SCRAPERS
from .storage import get_store


def run() -> int:
    store = get_store()

    # Telegram bilgisi: önce settings tablosu, sonra ortam değişkeni.
    chat_id = store.get_settings().get("telegram_chat_id") or config.TELEGRAM_CHAT_ID
    notifier = get_notifier(
        config.NOTIFY_BACKEND, token=config.TELEGRAM_BOT_TOKEN, chat_id=chat_id
    )

    filters = store.get_active_filters()
    known = store.get_known_prices()  # düşüş tespiti için ESKİ fiyatlar (kaydetmeden önce)

    products = []
    for scraper in SCRAPERS:
        name = scraper.__name__.split(".")[-1]
        try:
            found = scraper.scrape()
            products.extend(found)
            print(f"[{name}] {len(found)} ürün")
        except Exception as exc:  # bir site çökse de diğeri çalışsın
            print(f"[{name}] HATA: {exc}")

    print(f"Toplam {len(products)} ürün, {len(filters)} aktif filtre")

    events = detect_drops(products, known)
    store.save_products(products)  # current_price + price_history güncellenir
    print(f"{len(events)} fiyat düşüşü tespit edildi")

    sent = 0
    for ev in events:
        for f in filters:
            if not filter_matches(f, ev.product):
                continue
            if ev.drop_pct < (f.drop_threshold_pct or 0):
                continue
            if store.was_alerted(ev.product.url, f.id, ev.new_price):
                continue
            if notifier.send(format_drop_message(ev, f.label)):
                store.record_alert(ev.product.url, f.id, ev.old_price, ev.new_price)
                sent += 1

    print(f"{sent} bildirim gönderildi")
    return sent


if __name__ == "__main__":
    run()
