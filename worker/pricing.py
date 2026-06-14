"""Türkçe fiyat biçimi ayrıştırma/biçimlendirme ve model çıkarımı."""
from __future__ import annotations

import re

_PRICE_RE = re.compile(r"[\d.,]+")

# Ekran kartı modeli: RTX/GTX/RX/ARC + sayı + opsiyonel son ek (Ti/XT/SUPER/GRE/XTX)
_MODEL_RE = re.compile(
    r"\b(RTX|GTX|RX|ARC)\s*([A-Z]?\d{3,4})\s*(TI|XTX|XT|SUPER|GRE)?\b",
    re.IGNORECASE,
)

# İşlemci: AMD Ryzen (örn. "Ryzen 7 7800X3D") ve Intel Core (örn. "Core i5 12400F",
# "Core Ultra 7 265K").
_CPU_AMD_RE = re.compile(r"\bRyzen\s*(\d)\s*(\d{3,4}[A-Z0-9]{0,4})\b", re.IGNORECASE)
_CPU_INTEL_ULTRA_RE = re.compile(r"\bCore\s*Ultra\s*(\d)\s*(\d{3}[A-Z]{0,2})\b", re.IGNORECASE)
_CPU_INTEL_RE = re.compile(r"\bCore\s*(i[3579])\s*-?\s*(\d{4,5}[A-Z]{0,2})\b", re.IGNORECASE)

# RAM kapasitesi: "32GB", "16 GB" -> "32GB"
_RAM_RE = re.compile(r"\b(\d{1,3})\s*GB\b", re.IGNORECASE)


def _gpu_model(name: str) -> str | None:
    m = _MODEL_RE.search(name)
    if not m:
        return None
    prefix = m.group(1).upper()
    number = m.group(2).upper()
    suffix = m.group(3).upper() if m.group(3) else ""
    suffix = {"TI": "Ti", "XT": "XT", "XTX": "XTX", "SUPER": "SUPER", "GRE": "GRE"}.get(suffix, suffix)
    parts = [prefix, number] + ([suffix] if suffix else [])
    return " ".join(parts)


def _cpu_model(name: str) -> str | None:
    m = _CPU_AMD_RE.search(name)
    if m:
        return f"Ryzen {m.group(1)} {m.group(2).upper()}"
    m = _CPU_INTEL_ULTRA_RE.search(name)
    if m:
        return f"Core Ultra {m.group(1)} {m.group(2).upper()}"
    m = _CPU_INTEL_RE.search(name)
    if m:
        return f"Core {m.group(1).lower()} {m.group(2).upper()}"
    return None


def _ram_model(name: str) -> str | None:
    m = _RAM_RE.search(name)
    if m:
        return f"{int(m.group(1))}GB"
    return None


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


def extract_model(name: str | None, category: str | None = None) -> str | None:
    """Ürün adından normalize edilmiş model çıkarır (web önerileri/eşleşme için).
    Kategoriye göre doğru çıkarıcıyı seçer; kategori yoksa GPU->CPU->RAM sırasıyla dener.
    Hazır sistem gibi kategorilerde içindeki GPU modeli döner (5070'li kasaları yakalamak için)."""
    if not name:
        return None
    cat = (category or "").lower()

    if "ekran" in cat or "gpu" in cat:
        return _gpu_model(name)
    if "işlemci" in cat or "islemci" in cat or "cpu" in cat:
        return _cpu_model(name)
    if "ram" in cat or "bellek" in cat:
        return _ram_model(name)

    # Kategori bilinmiyor ya da hazır sistem/diğer: en ayırt edici olandan başla.
    return _gpu_model(name) or _cpu_model(name)
