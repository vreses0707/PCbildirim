"""Depolama arayüzü. SQLite (lokal) ve Supabase (bulut) backend'leri bunu uygular."""
from __future__ import annotations

from typing import Protocol

from ..models import Filter, Product


class Store(Protocol):
    def get_active_filters(self) -> list[Filter]:
        ...

    def get_known_prices(self) -> dict[str, float]:
        """{ürün_url: en_son_kaydedilen_fiyat}"""
        ...

    def save_products(self, products: list[Product]) -> None:
        """Ürünleri upsert eder; fiyat değiştiyse price_history'ye satır ekler."""
        ...

    def was_alerted(self, product_url: str, filter_id, new_price: float) -> bool:
        ...

    def record_alert(self, product_url: str, filter_id, old_price: float, new_price: float) -> None:
        ...

    def get_settings(self) -> dict:
        ...
