"""Filtre eşleştirme ve fiyat düşüşü tespiti."""
from __future__ import annotations

from dataclasses import dataclass

from .models import Filter, Product


def filter_matches(f: Filter, p: Product) -> bool:
    """Ürün, filtre kurallarına uyuyor mu? keywords AND, exclude_keywords dışlar."""
    name = p.name.lower()

    for kw in f.keywords:
        kw = kw.strip().lower()
        if kw and kw not in name:
            return False

    for kw in f.exclude_keywords:
        kw = kw.strip().lower()
        if kw and kw in name:
            return False

    if f.sites and p.site not in f.sites:
        return False

    # Normalize model seçildiyse tam eşleşme iste — "5070" ile "5070 Ti"yi net ayırır,
    # satıcının yazım farklarından ("5070TI" / "5070 Ti") etkilenmez.
    if f.model:
        if not p.model or p.model.strip().lower() != f.model.strip().lower():
            return False

    if f.category:
        if not p.category or f.category.strip().lower() not in p.category.lower():
            return False

    if f.max_price is not None and p.price > f.max_price:
        return False

    return True


@dataclass
class DropEvent:
    product: Product
    old_price: float
    new_price: float

    @property
    def drop_pct(self) -> float:
        if self.old_price <= 0:
            return 0.0
        return (self.old_price - self.new_price) / self.old_price * 100.0


def detect_drops(products: list[Product], known_prices: dict[str, float]) -> list[DropEvent]:
    """Daha önce kaydedilmiş fiyata (known_prices) göre düşenleri bulur.
    İlk çalıştırmada known_prices boştur -> hiç düşüş yok (spam olmaz)."""
    events: list[DropEvent] = []
    for p in products:
        old = known_prices.get(p.url)
        if old is not None and p.price < old:
            events.append(DropEvent(product=p, old_price=old, new_price=p.price))
    return events
