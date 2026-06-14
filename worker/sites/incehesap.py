"""incehesap.com scraper.

Her ürün kartı <a class="product" data-product='{...json...}'> taşır; JSON içinde
ad, marka, fiyat (sayı olarak) hazır gelir — kırılgan DOM yerine bunu kullanırız.
Görsel için data-gaitem JSON'undaki 'image' alanı.
Sayfalama: /{slug}/sayfa-N/  (1. sayfa /{slug}/)
"""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from ..config import INCEHESAP_CATEGORIES, MAX_PAGES
from ..fetch import get
from ..models import Product
from ..pricing import extract_model

BASE = "https://www.incehesap.com"
SITE = "incehesap"


def _abs_url(href: str) -> str:
    if not href:
        return ""
    return href if href.startswith("http") else BASE + href


def _parse_page(html: str, category: str | None) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []
    for a in soup.select("a.product[data-product]"):
        try:
            data = json.loads(a.get("data-product"))
        except (TypeError, ValueError):
            continue
        name = data.get("name")
        price = data.get("price")
        if not name or not price:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        image = None
        gaitem = a.get("data-gaitem")
        if gaitem:
            try:
                image = json.loads(gaitem).get("image")
            except (TypeError, ValueError):
                pass

        cat = data.get("category") or category
        products.append(
            Product(
                url=_abs_url(a.get("href", "")),
                site=SITE,
                name=name,
                price=price,
                category=cat,
                brand=data.get("brand"),
                model=extract_model(name, cat),
                image=image,
            )
        )
    return products


def scrape_campaign(slug: str, name: str) -> list[Product]:
    """Tek bir incehesap fırsat sayfasını tarar (normal ürün yapısını kullanır)."""
    seen: dict[str, Product] = {}
    for pg in range(1, MAX_PAGES + 1):
        url = f"{BASE}/{slug}/" + (f"sayfa-{pg}/" if pg > 1 else "")
        resp = get(url)
        if resp.status_code != 200:
            break
        new = [p for p in _parse_page(resp.text, None) if p.url not in seen]
        for p in new:
            p.campaign = name
            seen[p.url] = p
        if not new:
            break
    return list(seen.values())


def scrape(categories=None) -> list[Product]:
    categories = categories or INCEHESAP_CATEGORIES
    seen: dict[str, Product] = {}
    for cat in categories:
        slug = cat["slug"]
        cname = cat.get("category")
        for pg in range(1, MAX_PAGES + 1):
            url = f"{BASE}/{slug}/" + (f"sayfa-{pg}/" if pg > 1 else "")
            resp = get(url)
            if resp.status_code != 200:
                print(f"[incehesap] {url} -> HTTP {resp.status_code}")
                break
            page_products = _parse_page(resp.text, cname)
            new = [p for p in page_products if p.url not in seen]
            for p in new:
                seen[p.url] = p
            if not new:
                break
    return list(seen.values())


if __name__ == "__main__":  # python -m worker.sites.incehesap
    items = scrape()
    print(f"incehesap: {len(items)} ürün")
    for p in items[:5]:
        print(f"  {p.price:>12,.2f}  {p.model or '-':<14}  {p.name[:60]}")
