"""Veri modelleri (saf dataclass'lar)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    url: str                 # kanonik kimlik (ürün detay linki)
    site: str                # "itopya" | "incehesap"
    name: str
    price: float
    category: str | None = None
    brand: str | None = None
    model: str | None = None   # örn. "RTX 5070 Ti" (öneri kataloğu için)
    image: str | None = None


@dataclass
class Filter:
    """Kullanıcının takip kuralı. Tüm keywords AND'lenir; exclude'lar dışlar."""
    id: int | str
    label: str
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)   # boş = tüm siteler
    category: str | None = None
    model: str | None = None     # normalize model (örn. "RTX 5070") -> tam eşleşme
    max_price: float | None = None
    drop_threshold_pct: float = 2.0
    active: bool = True
