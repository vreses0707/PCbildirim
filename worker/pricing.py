"""Türkçe fiyat biçimi ayrıştırma/biçimlendirme ve model çıkarımı."""
from __future__ import annotations

import re

_PRICE_RE = re.compile(r"[\d.,]+")

# Ekran kartı modeli: RTX/GTX/RX/ARC + sayı + opsiyonel son ek (Ti/XT/SUPER/GRE/XTX)
_MODEL_RE = re.compile(
    r"\b(RTX|GTX|RX|ARC)\s*([A-Z]?\d{3,4})\s*(TI|XTX|XT|SUPER|GRE)?\b",
    re.IGNORECASE,
)


def parse_turkish_price(text) -> float | None:
    """'35.391,32 TL' -> 35391.32 ; '17.399 TL' -> 17399.0 ; '34.999' -> 34999.0"""
    if text is None:
        return None
    m = _PRICE_RE.search(str(text))
    if not m:
        return None
    num = m.group(0).strip(".,")
    # Binlik ayıracı '.' kaldır, ondalık ',' -> '.'
    num = num.replace(".", "").replace(",", ".")
    try:
        val = float(num)
    except ValueError:
        return None
    return val if val > 0 else None


def format_price(value: float | None) -> str:
    """34999.0 -> '34.999 TL' ; 35391.32 -> '35.391,32 TL'"""
    if value is None:
        return "-"
    whole = int(value)
    frac = round((value - whole) * 100)
    s = f"{whole:,}".replace(",", ".")
    if frac:
        s += f",{frac:02d}"
    return s + " TL"


def extract_model(name: str | None) -> str | None:
    """Ürün adından normalize edilmiş GPU modeli çıkarır (öneri kataloğu için)."""
    if not name:
        return None
    m = _MODEL_RE.search(name)
    if not m:
        return None
    prefix = m.group(1).upper()
    number = m.group(2).upper()
    suffix = m.group(3).upper() if m.group(3) else ""
    suffix = {"TI": "Ti", "XT": "XT", "XTX": "XTX", "SUPER": "SUPER", "GRE": "GRE"}.get(suffix, suffix)
    parts = [prefix, number] + ([suffix] if suffix else [])
    return " ".join(parts)
