"""Yerel SQLite depolama — hesap/secret gerektirmez, geliştirme ve test için.

Supabase şemasının birebir aynısını yerelde taklit eder; böylece worker mantığını
buluta bağlanmadan uçtan uca test edebilirsin.
"""
from __future__ import annotations

import json
import sqlite3
import time

from ..models import Filter, Product

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    url           TEXT PRIMARY KEY,
    site          TEXT,
    name          TEXT,
    category      TEXT,
    brand         TEXT,
    model         TEXT,
    image         TEXT,
    current_price REAL,
    last_seen_at  REAL
);
CREATE TABLE IF NOT EXISTS price_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_url TEXT,
    price       REAL,
    seen_at     REAL
);
CREATE TABLE IF NOT EXISTS filters (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    label              TEXT,
    keywords           TEXT,   -- JSON array
    exclude_keywords   TEXT,   -- JSON array
    sites              TEXT,   -- JSON array
    category           TEXT,
    model              TEXT,   -- normalize model (örn. "RTX 5070"), tam eşleşme
    max_price          REAL,
    drop_threshold_pct REAL DEFAULT 2,
    active             INTEGER DEFAULT 1,
    created_at         REAL
);
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_url TEXT,
    filter_id   INTEGER,
    old_price   REAL,
    new_price   REAL,
    sent_at     REAL
);
CREATE TABLE IF NOT EXISTS settings (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    telegram_chat_id TEXT
);
INSERT OR IGNORE INTO settings (id, telegram_chat_id) VALUES (1, NULL);
"""


def _loads(text) -> list[str]:
    if not text:
        return []
    try:
        val = json.loads(text)
        return val if isinstance(val, list) else []
    except (TypeError, ValueError):
        # virgülle ayrılmış de olabilir
        return [s.strip() for s in str(text).split(",") if s.strip()]


class SqliteStore:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- filtreler ---
    def get_active_filters(self) -> list[Filter]:
        rows = self.conn.execute("SELECT * FROM filters WHERE active = 1").fetchall()
        return [
            Filter(
                id=r["id"],
                label=r["label"] or "",
                keywords=_loads(r["keywords"]),
                exclude_keywords=_loads(r["exclude_keywords"]),
                sites=_loads(r["sites"]),
                category=r["category"],
                model=r["model"],
                max_price=r["max_price"],
                drop_threshold_pct=r["drop_threshold_pct"] or 2.0,
                active=bool(r["active"]),
            )
            for r in rows
        ]

    # --- ürünler / fiyat ---
    def get_known_prices(self) -> dict[str, float]:
        rows = self.conn.execute("SELECT url, current_price FROM products").fetchall()
        return {r["url"]: r["current_price"] for r in rows if r["current_price"] is not None}

    def save_products(self, products: list[Product]) -> None:
        now = time.time()
        cur = self.conn.cursor()
        existing = self.get_known_prices()
        for p in products:
            old = existing.get(p.url)
            cur.execute(
                """
                INSERT INTO products (url, site, name, category, brand, model, image,
                                      current_price, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    site=excluded.site, name=excluded.name, category=excluded.category,
                    brand=excluded.brand, model=excluded.model, image=excluded.image,
                    current_price=excluded.current_price, last_seen_at=excluded.last_seen_at
                """,
                (p.url, p.site, p.name, p.category, p.brand, p.model, p.image, p.price, now),
            )
            if old is None or old != p.price:
                cur.execute(
                    "INSERT INTO price_history (product_url, price, seen_at) VALUES (?, ?, ?)",
                    (p.url, p.price, now),
                )
        self.conn.commit()

    # --- bildirim dedup/log ---
    def was_alerted(self, product_url: str, filter_id, new_price: float) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM alerts WHERE product_url=? AND filter_id=? AND new_price=? LIMIT 1",
            (product_url, filter_id, new_price),
        ).fetchone()
        return row is not None

    def record_alert(self, product_url, filter_id, old_price, new_price) -> None:
        self.conn.execute(
            "INSERT INTO alerts (product_url, filter_id, old_price, new_price, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (product_url, filter_id, old_price, new_price, time.time()),
        )
        self.conn.commit()

    # --- ayarlar ---
    def get_settings(self) -> dict:
        row = self.conn.execute("SELECT telegram_chat_id FROM settings WHERE id=1").fetchone()
        return {"telegram_chat_id": row["telegram_chat_id"] if row else None}
