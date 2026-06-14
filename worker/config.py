import os


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if val not in (None, "") else default


USER_AGENT = _env(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
REQUEST_TIMEOUT = int(_env("REQUEST_TIMEOUT", "30"))
REQUEST_DELAY = float(_env("REQUEST_DELAY", "1.5"))
MAX_PAGES = int(_env("MAX_PAGES", "15"))

DEFAULT_DROP_THRESHOLD_PCT = float(_env("DEFAULT_DROP_THRESHOLD_PCT", "2.0"))

# Sitelerin kampanya/fırsat sayfalarını otomatik bulup yeni giren ürünleri bildirir.
CAMPAIGNS_ENABLED = _env("CAMPAIGNS", "1") not in ("0", "false", "False")
MAX_CAMPAIGN_NOTIFS = int(_env("MAX_CAMPAIGN_NOTIFS", "30"))

STORE_BACKEND = _env("STORE", "sqlite")
SQLITE_PATH = _env("SQLITE_PATH", "pcbildirim.db")
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_SERVICE_KEY")

NOTIFY_BACKEND = _env("NOTIFY", "console")
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

ITOPYA_CATEGORIES = [
    {"slug": "ekran-karti_k11", "category": "Ekran Kartı"},
    {"slug": "oem-paketler", "category": "Hazır Sistem"},
    {"slug": "islemci_k8", "category": "İşlemci"},
    {"slug": "anakart_k9", "category": "Anakart"},
    {"slug": "rambellek_k10", "category": "RAM"},
    {"slug": "ssd_k22", "category": "SSD"},
    {"slug": "cpu-sogutma_k13", "category": "Soğutma"},
    {"slug": "kasa_k12", "category": "Kasa"},
    {"slug": "guc-kaynagi_k16", "category": "Güç Kaynağı"},
]

INCEHESAP_CATEGORIES = [
    {"slug": "ekran-karti-fiyatlari", "category": "Ekran Kartı"},
    {"slug": "hazir-sistemler-fiyatlari", "category": "Hazır Sistem"},
    {"slug": "gaming-pc-fiyatlari", "category": "Hazır Sistem"},
    {"slug": "islemci-fiyatlari", "category": "İşlemci"},
    {"slug": "anakart-fiyatlari", "category": "Anakart"},
    {"slug": "ram-fiyatlari", "category": "RAM"},
    {"slug": "ssd-harddisk-fiyatlari", "category": "SSD"},
    {"slug": "cpu-sogutma-fiyatlari", "category": "Soğutma"},
    {"slug": "kasa-fiyatlari", "category": "Kasa"},
    {"slug": "guc-kaynagi-fiyatlari", "category": "Güç Kaynağı"},
]
