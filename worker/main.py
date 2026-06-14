"""Orkestrasyon: scrape -> kaydet -> düşüş tespiti -> eşleştir -> bildir.

İki bildirim yolu:
  1) Fiyat düşüşü: normal kategorilerde, kullanıcı filtrelerine göre düşüş.
  2) Kampanya: sitelerin fırsat/kampanya sayfalarına yeni giren ürünler.

Çalıştırma:
    python -m worker.main          # bir kez tarar
Ortam:
    STORE=sqlite|supabase   NOTIFY=console|telegram   CAMPAIGNS=1|0
"""
from __future__ import annotations

from . import config
from .campaigns import discover_incehesap, discover_itopya
from .match import detect_drops, filter_matches
from .notify import format_campaign_message, format_drop_message, get_notifier
from .sites import SCRAPERS, incehesap, itopya
from .storage import get_store


def _scrape_campaigns() -> list:
    """Keşfedilen kampanya sayfalarını tarar; ürünleri (url'e göre tekil) döndürür.
    itopya ve incehesap kampanya sayfaları farklı yapıda olduğu için her sitenin
    kendi scrape_campaign'i kullanılır."""
    found: dict[str, object] = {}
    plan = [
        ("itopya", itopya.scrape_campaign, discover_itopya()),
        ("incehesap", incehesap.scrape_campaign, discover_incehesap()),
    ]
    for site, scrape_campaign, sources in plan:
        for c in sources:
            try:
                prods = scrape_campaign(c["slug"], c["name"])
            except Exception as exc:
                print(f"[kampanya/{site}] {c['slug']} HATA: {exc}")
                continue
            for p in prods:
                found.setdefault(p.url, p)
            if prods:
                print(f"[kampanya/{site}] {c['name']}: {len(prods)} ürün")
    return list(found.values())


def _run_campaigns(store, filters, notifier) -> int:
    """Kampanya sayfalarına yeni giren ürünleri bildirir.
    İlk taramada mevcut tüm fırsatları baz alır (sel olmaz), sonraki taramalarda
    yalnızca YENİ girenleri bildirir."""
    products = _scrape_campaigns()
    print(f"[kampanya] toplam {len(products)} fırsat ürünü")
    if not products:
        return 0

    seen = store.get_campaign_seen()
    first_run = len(seen) == 0
    new_items = [p for p in products if (p.url, p.campaign) not in seen]

    sent = 0
    processed = []
    for p in new_items:
        if sent >= config.MAX_CAMPAIGN_NOTIFS:
            break  # taşanlar sonraki taramaya kalsın (kaydetmiyoruz)
        # Eşleşme: aktif filtre varsa filtreye uyanları, hiç filtre yoksa hepsini.
        wants = (not filters) or any(filter_matches(f, p) for f in filters)
        # İlk taramada filtre YOKKEN hepsini bildirmek sel yaratır → sessiz baz al.
        # Ama filtreyle eşleşen MEVCUT fırsatları ilk taramada da bildir.
        if first_run and not filters:
            wants = False
        if wants and notifier.send(format_campaign_message(p)):
            sent += 1
        processed.append(p)

    store.save_campaign_products(processed)
    if first_run:
        notifier.send(
            f"🔥 Kampanya takibi başladı. {len(products)} fırsat ürünü izleniyor; "
            f"bundan sonra fırsat sayfalarına yeni gireni hemen bildireceğim."
        )
        print(f"[kampanya] ilk tarama — {len(products)} ürün baz alındı, {sent} bildirim")
    else:
        print(f"[kampanya] {len(new_items)} yeni ürün, {sent} bildirim gönderildi")
    return sent


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

    # 2) Kampanya/fırsat sayfası takibi
    if config.CAMPAIGNS_ENABLED:
        try:
            sent += _run_campaigns(store, filters, notifier)
        except Exception as exc:
            print(f"[kampanya] HATA: {exc}")

    return sent


if __name__ == "__main__":
    run()
