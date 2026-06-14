"""Kampanya/fırsat sayfalarını OTOMATİK keşfet.

Sitelerin asıl indirimleri ("Kara Cuma", "Karne Fırsatları", "Yaz Fırsatları" gibi)
genelde ayrı bir kampanya sayfasında olur; normal kategori listesinde fiyat değişmez.
Bu yüzden her taramada ana sayfadaki menüden fırsat/kampanya sayfası linklerini
buluruz. Kampanya adı değişse de otomatik yakalanır — sabit link yazmayız.

Döndürülen her öğe site scraper'larının `scrape(categories=...)` formatına uyar:
    {"slug": "<site üzerindeki yol>", "name": "<kampanya adı>"}
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .fetch import get

ITOPYA_BASE = "https://www.itopya.com"
INCEHESAP_BASE = "https://www.incehesap.com"

# Link adresinde/metninde bunlardan biri geçiyorsa kampanya sayfası say.
_CAMPAIGN_WORDS = (
    "firsat", "fırsat", "kampanya", "indirim", "outlet", "karne",
    "kara-cuma", "karacuma", "black-friday", "blackfriday", "yaz-firsat",
    "kis-firsat", "bahar-firsat", "sezon", "ozel-gun", "mega",
)


def _looks_campaign(href: str, text: str) -> bool:
    blob = (href + " " + (text or "")).lower()
    return any(w in blob for w in _CAMPAIGN_WORDS)


def _slug(href: str, host: str) -> str | None:
    """Linkten site içi yolu çıkarır. Farklı siteye giden linkler için None."""
    u = urlparse(href)
    if u.netloc and host not in u.netloc:
        return None
    return (u.path or "").strip("/") or None


def _name_from_slug(slug: str) -> str:
    """'super-karne-firsatlari_s896' -> 'Super Karne Firsatlari' gibi okunur ad."""
    base = slug.split("/")[-1]
    base = re.sub(r"_s\d+$", "", base)   # itopya _s### son eki
    base = re.sub(r"-d\d+$", "", base)   # incehesap -d#### son eki
    return base.replace("-", " ").strip().title() or slug


def _pick_name(text: str, slug: str) -> str:
    text = (text or "").strip()
    if text and not text.lower().startswith("http"):
        return text
    return _name_from_slug(slug)


def discover_itopya() -> list[dict]:
    """itopya ana sayfasındaki kampanya menüsünden fırsat sayfalarını bul.
    itopya'da özel listeleme sayfaları '..._s<rakam>' biçimindedir."""
    try:
        resp = get(ITOPYA_BASE)
        if resp.status_code != 200:
            print(f"[kampanya/itopya] ana sayfa HTTP {resp.status_code}")
            return []
    except Exception as exc:
        print(f"[kampanya/itopya] ana sayfa hatası: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not re.search(r"_s\d+", href):       # itopya özel listeleme sayfası değilse atla
            continue
        if not _looks_campaign(href, text):
            continue
        slug = _slug(href, "itopya.com")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append({"slug": slug, "name": _pick_name(text, slug)})
    return out


def discover_incehesap() -> list[dict]:
    """incehesap ana sayfasından ürün listeleyen fırsat sayfalarını bul.
    '/icerik/...' linkleri içerik/banner sayfasıdır, ürün listelemez — atlanır."""
    sources: list[dict] = []
    seen: set[str] = set()
    try:
        resp = get(INCEHESAP_BASE)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                low = href.lower()
                if "/icerik/" in low:
                    continue
                if not ("firsat" in low or "fırsat" in low or "outlet" in low):
                    continue
                slug = _slug(href, "incehesap.com")
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                sources.append({"slug": slug, "name": _pick_name(a.get_text(strip=True), slug)})
        else:
            print(f"[kampanya/incehesap] ana sayfa HTTP {resp.status_code}")
    except Exception as exc:
        print(f"[kampanya/incehesap] ana sayfa hatası: {exc}")

    # Bilinen sabit fırsat sayfası — her zaman kontrol et.
    if "firsatlar" not in seen:
        sources.append({"slug": "firsatlar", "name": "Fırsat Ürünleri"})
    return sources
