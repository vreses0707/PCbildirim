"""itopya.com scraper.

Ürün kartı: <div class="product" data-urun-id="...">
  ad+link:  <a class="title" href="/...._u33512">Ad</a>
  fiyat:    <span class="product-price"><strong>35.391,32 TL</strong></span>
Sayfalama: ?pg=N  (1. sayfa parametresiz)
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from ..config import ITOPYA_CATEGORIES, MAX_PAGES
from ..fetch import get
from ..models import Product
from ..pricing import extract_model, parse_turkish_price

BASE = "https://www.itopya.com"
SITE = "itopya"


def _abs_url(href: str) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else BASE + href


def _parse_page(html: str, category: str | None) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []
    for block in soup.select("div.product[data-urun-id]"):
        a = block.select_one("a.title")
        if a is None:
            continue
        name = a.get_text(strip=True)
        url = _abs_url(a.get("href", ""))
        price_el = block.select_one("span.product-price strong") or block.select_one(
            "span.product-price"
        )
        price = parse_turkish_price(price_el.get_text()) if price_el else None
        if not name or not url or price is None:
            continue
        brand = name.split()[0] if name.split() else None
        products.append(
            Product(
                url=url,
                site=SITE,
                name=name,
                price=price,
                category=category,
                brand=brand,
                model=extract_model(name, category),
            )
        )
    return products


def _parse_campaign_page(html: str, campaign_name: str) -> list[Product]:
    """itopya kampanya/fırsat sayfaları farklı yapıdadır: <a class="ss-card"> kartlar,
    ad `.ss-product-description`, fiyatlar `.old-price` / `.new-price`."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []
    for card in soup.select("a.ss-card"):
        url = _abs_url(card.get("href", ""))
        desc = card.select_one(".ss-product-description")
        title = card.select_one(".ss-product-title")
        name = (desc.get_text(strip=True) if desc else "") or (
            title.get_text(strip=True) if title else ""
        )
        new_el = card.select_one(".new-price")
        old_el = card.select_one(".old-price")
        price = parse_turkish_price(new_el.get_text()) if new_el else None
        old = parse_turkish_price(old_el.get_text()) if old_el else None
        if old is not None and price is not None and old <= price:
            old = None  # bazı kartlarda eski fiyat JS ile gelir; placeholder'ı yok say
        if not name or not url or price is None:
            continue
        brand = name.split()[0] if name.split() else None
        products.append(
            Product(
                url=url,
                site=SITE,
                name=name,
                price=price,
                brand=brand,
                model=extract_model(name),
                campaign=campaign_name,
                old_price=old,
            )
        )
    return products


def scrape_campaign(slug: str, name: str) -> list[Product]:
    """Tek bir itopya kampanya sayfasını (gerekirse sayfalama ile) tarar."""
    seen: dict[str, Product] = {}
    for pg in range(1, MAX_PAGES + 1):
        url = f"{BASE}/{slug}" + (f"?pg={pg}" if pg > 1 else "")
        resp = get(url)
        if resp.status_code != 200:
            break
        new = [p for p in _parse_campaign_page(resp.text, name) if p.url not in seen]
        for p in new:
            seen[p.url] = p
        if not new:
            break
    return list(seen.values())


def scrape(categories=None) -> list[Product]:
    categories = categories or ITOPYA_CATEGORIES
    seen: dict[str, Product] = {}
    for cat in categories:
        slug = cat["slug"]
        cname = cat.get("category")
        for pg in range(1, MAX_PAGES + 1):
            url = f"{BASE}/{slug}" + (f"?pg={pg}" if pg > 1 else "")
            resp = get(url)
            if resp.status_code != 200:
                print(f"[itopya] {url} -> HTTP {resp.status_code}")
                break
            page_products = _parse_page(resp.text, cname)
            new = [p for p in page_products if p.url not in seen]
            for p in new:
                seen[p.url] = p
            if not new:  # daha fazla ürün yok / sayfa tekrarladı
                break
    return list(seen.values())


if __name__ == "__main__":  # hızlı manuel test: python -m worker.sites.itopya
    items = scrape()
    print(f"itopya: {len(items)} ürün")
    for p in items[:5]:
        print(f"  {p.price:>12,.2f}  {p.model or '-':<14}  {p.name[:60]}")
