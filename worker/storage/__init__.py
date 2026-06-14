"""Depolama backend seçimi (config.STORE_BACKEND)."""
from __future__ import annotations

from .. import config
from .base import Store


def get_store() -> Store:
    backend = (config.STORE_BACKEND or "sqlite").lower()
    if backend == "supabase":
        if not (config.SUPABASE_URL and config.SUPABASE_KEY):
            raise RuntimeError(
                "STORE=supabase için SUPABASE_URL ve SUPABASE_SERVICE_KEY gerekli."
            )
        from .supabase_store import SupabaseStore

        return SupabaseStore(config.SUPABASE_URL, config.SUPABASE_KEY)

    from .sqlite_store import SqliteStore

    return SqliteStore(config.SQLITE_PATH)
