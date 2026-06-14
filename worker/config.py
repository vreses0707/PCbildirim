"""Yapılandırma — her şey ortam değişkenlerinden okunur, makul varsayılanlarla.

Lokal test için hiçbir şey ayarlamana gerek yok:
  STORE=sqlite (varsayılan)  -> yerel pcbildirim.db dosyası
  NOTIFY=console (varsayılan) -> bildirimler ekrana yazılır

Buluta geçerken:
  STORE=supabase  + SUPABASE_URL + SUPABASE_SERVICE_KEY
  NOTIFY=telegram + TELEGRAM_BOT_TOKEN (+ TELEGRAM_CHAT_ID veya settings tablosu)
"""
import os


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if val not in (None, "") else default


# --- HTTP / scraping ---
USER_AGENT = _env(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
REQUEST_TIMEOUT = int(_env("REQUEST_TIMEOUT", "30"))
REQUEST_DELAY = float(_env("REQUEST_DELAY", "1.0"))  # sayfalar arası nazik bekleme (sn)
MAX_PAGES = int(_env("MAX_PAGES", "15"))             # kategori başına azami sayfa

# --- Eşleştirme / bildirim ---
DEFAULT_DROP_THRESHOLD_PCT = float(_env("DEFAULT_DROP_THRESHOLD_PCT", "2.0"))

# --- Depolama ---
STORE_BACKEND = _env("STORE", "sqlite")             # sqlite | supabase
SQLITE_PATH = _env("SQLITE_PATH", "pcbildirim.db")
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_SERVICE_KEY")

# --- Bildirim kanalı ---
NOTIFY_BACKEND = _env("NOTIFY", "console")          # console | telegram
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# --- Hangi kategoriler taranacak ---
# slug: site üzerindeki kategori yolu. category: ürünlere yazılacak okunur etiket.
# İlk MVP'de doğrulanmış olan ekran kartı aktif; diğerlerini açmak için yorumu kaldır.
ITOPYA_CATEGORIES = [
    {"slug": "ekran-karti_k11", "category": "Ekran Kartı"},
    # {"slug": "islemci_k8", "category": "İşlemci"},
    # {"slug": "anakart_k9", "category": "Anakart"},
    # {"slug": "oem-paketler", "category": "Hazır Sistem"},
]

INCEHESAP_CATEGORIES = [
    {"slug": "ekran-karti-fiyatlari", "category": "Ekran Kartı"},
    # {"slug": "islemci-fiyatlari", "category": "İşlemci"},
    # {"slug": "anakart-fiyatlari", "category": "Anakart"},
    # {"slug": "hazir-sistemler-fiyatlari", "category": "Hazır Sistem"},
]
