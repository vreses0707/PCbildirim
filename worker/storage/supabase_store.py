"""Supabase (Postgres) depolama — bulut/üretim modu.

Web arayüzü ile worker'ın paylaştığı kalıcı veritabanı. `supabase` paketi sadece
bu modda gerekir (requirements'ta yorumlu); STORE=supabase iken kurman gerekir.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import Filter, Product


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [s.strip() for s in str(val).split(",") if s.strip()]


class SupabaseStore:
    def __init__(self, url: str, key: str):
        # Lazy import: paket yalnızca bu mod kullanılırken gerekli olsun.
        from supabase import create_client

        self.client = create_client(url, key)

    def get_active_filters(self) -> list[Filter]:
        res = self.client.table("filters").select("*").eq("active", True).execute()
        out: list[Filter] = []
        for r in res.data or []:
            out.append(
                Filter(
                    id=r["id"],
                    label=r.get("label") or "",
                    keywords=_as_list(r.get("keywords")),
                    exclude_keywords=_as_list(r.get("exclude_keywords")),
                    sites=_as_list(r.get("sites")),
                    category=r.get("category"),
                    model=r.get("model"),
                    max_price=r.get("max_price"),
                    drop_threshold_pct=r.get("drop_threshold_pct") or 2.0,
                    active=bool(r.get("active", True)),
                )
            )
        return out

    def get_known_prices(self) -> dict[str, float]:
        res = self.client.table("products").select("url, current_price").execute()
        return {
            r["url"]: r["current_price"]
            for r in (res.data or [])
            if r.get("current_price") is not None
        }

    def save_products(self, products: list[Product]) -> None:
        if not products:
            return
        existing = self.get_known_prices()
        now = _now_iso()
        rows = [
            {
                "url": p.url,
                "site": p.site,
                "name": p.name,
                "category": p.category,
                "brand": p.brand,
                "model": p.model,
                "image": p.image,
                "current_price": p.price,
                "last_seen_at": now,
            }
            for p in products
        ]
        # Tek seferde upsert (büyük listede parçalara böl).
        for i in range(0, len(rows), 500):
            self.client.table("products").upsert(rows[i : i + 500]).execute()

        history = [
            {"product_url": p.url, "price": p.price, "seen_at": now}
            for p in products
            if existing.get(p.url) != p.price
        ]
        for i in range(0, len(history), 500):
            if history[i : i + 500]:
                self.client.table("price_history").insert(history[i : i + 500]).execute()

    def was_alerted(self, product_url: str, filter_id, new_price: float) -> bool:
        res = (
            self.client.table("alerts")
            .select("id")
            .eq("product_url", product_url)
            .eq("filter_id", filter_id)
            .eq("new_price", new_price)
            .limit(1)
            .execute()
        )
        return bool(res.data)

    def record_alert(self, product_url, filter_id, old_price, new_price) -> None:
        self.client.table("alerts").insert(
            {
                "product_url": product_url,
                "filter_id": filter_id,
                "old_price": old_price,
                "new_price": new_price,
                "sent_at": _now_iso(),
            }
        ).execute()

    def get_settings(self) -> dict:
        res = self.client.table("settings").select("*").eq("id", 1).limit(1).execute()
        if res.data:
            return {"telegram_chat_id": res.data[0].get("telegram_chat_id")}
        return {"telegram_chat_id": None}

    # --- kampanya ürünleri ---
    def get_campaign_seen(self) -> set:
        res = self.client.table("campaign_products").select("url, campaign").execute()
        return {(r["url"], r.get("campaign")) for r in (res.data or [])}

    def save_campaign_products(self, products) -> None:
        if not products:
            return
        now = _now_iso()
        rows = [
            {
                "url": p.url,
                "site": p.site,
                "name": p.name,
                "campaign": p.campaign,
                "price": p.price,
                "first_seen_at": now,
            }
            for p in products
        ]
        for i in range(0, len(rows), 500):
            self.client.table("campaign_products").upsert(
                rows[i : i + 500], on_conflict="url,campaign"
            ).execute()
