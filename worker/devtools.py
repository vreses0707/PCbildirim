"""Lokal test/yönetim yardımcıları (yalnızca SQLite modunda anlamlı).

Örnekler:
    python -m worker.devtools add-filter --label "RTX 5070" --keywords 5070 --exclude "5070 ti" --threshold 0
    python -m worker.devtools list-filters
    python -m worker.devtools list-products --like 5070
    python -m worker.devtools bump --like 5070 --pct 10   # kayıtlı fiyatı %10 yükselt
                                                          # -> sonraki run'da "düşüş" tetikler (test için)
"""
from __future__ import annotations

import argparse
import json
import time

from . import config
from .storage.sqlite_store import SqliteStore


def _store() -> SqliteStore:
    return SqliteStore(config.SQLITE_PATH)


def add_filter(args) -> None:
    s = _store()
    s.conn.execute(
        "INSERT INTO filters (label, keywords, exclude_keywords, sites, category, "
        "model, max_price, drop_threshold_pct, active, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            args.label,
            json.dumps([k.strip() for k in (args.keywords or [])]),
            json.dumps([k.strip() for k in (args.exclude or [])]),
            json.dumps([k.strip() for k in (args.sites or [])]),
            args.category,
            args.model,
            args.max_price,
            args.threshold,
            1,
            time.time(),
        ),
    )
    s.conn.commit()
    print(f"Filtre eklendi: {args.label}")


def list_models(args) -> None:
    """Kayıtlı ürünlerden çıkan normalize modeller (web önerileri bunlardan beslenir)."""
    s = _store()
    rows = s.conn.execute(
        "SELECT model, COUNT(*) n FROM products WHERE model IS NOT NULL "
        "GROUP BY model ORDER BY n DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['n']:>4} ürün  {r['model']}")


def list_filters(args) -> None:
    s = _store()
    for r in s.conn.execute("SELECT * FROM filters").fetchall():
        durum = "aktif" if r["active"] else "pasif"
        print(
            f"#{r['id']} [{durum}] {r['label']} | "
            f"kw={r['keywords']} exclude={r['exclude_keywords']} "
            f"max={r['max_price']} esik=%{r['drop_threshold_pct']}"
        )


def list_products(args) -> None:
    s = _store()
    q = "SELECT site, current_price, model, name, url FROM products"
    params: tuple = ()
    if args.like:
        q += " WHERE name LIKE ?"
        params = (f"%{args.like}%",)
    q += " ORDER BY current_price LIMIT ?"
    params += (args.limit,)
    for r in s.conn.execute(q, params).fetchall():
        print(f"  {r['current_price']:>12,.2f}  {r['site']:<10} {r['model'] or '-':<12} {r['name'][:55]}")


def bump(args) -> None:
    """Kayıtlı fiyatı yükselt — bir sonraki run'da yapay 'fiyat düşüşü' üretmek için."""
    s = _store()
    cur = s.conn.execute(
        "UPDATE products SET current_price = current_price * ? WHERE name LIKE ?",
        (1 + args.pct / 100.0, f"%{args.like}%"),
    )
    s.conn.commit()
    print(f"{cur.rowcount} ürünün kayıtlı fiyatı %{args.pct} yükseltildi (test amaçlı).")


def main() -> None:
    ap = argparse.ArgumentParser(description="PCbildirim lokal yardımcılar")
    sub = ap.add_subparsers(required=True)

    a = sub.add_parser("add-filter")
    a.add_argument("--label", required=True)
    a.add_argument("--keywords", nargs="*", default=[])
    a.add_argument("--exclude", nargs="*", default=[])
    a.add_argument("--sites", nargs="*", default=[])
    a.add_argument("--category", default=None)
    a.add_argument("--model", default=None, help="Normalize model, örn. 'RTX 5070'")
    a.add_argument("--max-price", dest="max_price", type=float, default=None)
    a.add_argument("--threshold", type=float, default=config.DEFAULT_DROP_THRESHOLD_PCT)
    a.set_defaults(func=add_filter)

    a = sub.add_parser("list-filters")
    a.set_defaults(func=list_filters)

    a = sub.add_parser("list-models")
    a.set_defaults(func=list_models)

    a = sub.add_parser("list-products")
    a.add_argument("--like", default=None)
    a.add_argument("--limit", type=int, default=20)
    a.set_defaults(func=list_products)

    a = sub.add_parser("bump")
    a.add_argument("--like", required=True)
    a.add_argument("--pct", type=float, default=10.0)
    a.set_defaults(func=bump)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
