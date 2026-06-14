# 🖥️ PC Fırsat Bildirim

**itopya.com** ve **incehesap.com**'da takip ettiğin ürünler (örn. "RTX 5070")
**ucuzlayınca Telegram'dan otomatik haber** veren sistem. Filtrelerini bir **web
arayüzünden**, model/marka önerileriyle eklersin; tarama **7/24 ücretsiz** olarak
GitHub Actions'ta çalışır.

```
[Web arayüzü]  ──>  [Supabase (Postgres)]  <──  [GitHub Actions worker]
 filtre ekle/yönet    filtreler / ürünler /        her 20 dk: tara → fiyat
 (model önerileri)     fiyat geçmişi / uyarılar      düştü mü? → Telegram
                                                            │
                                                      [Telegram botu]
```

- **Tetikleyici:** sadece **fiyat düşüşü** (önceki taramaya göre). Ufak dalgalanmaları
  elemek için filtre başına **düşüş eşiği %** (varsayılan %2) + tekrar bildirim engelleme.
- **Eşleştirme:** normalize **model** (tam eşleşme; "RTX 5070" seçince "5070 Ti" gelmez)
  + opsiyonel **anahtar kelime / hariç tutma / maks. fiyat / site**.

---

## 1) Hızlı yerel deneme (hesap gerekmez)

Her şeyi buluta taşımadan önce mantığı kendi bilgisayarında SQLite + ekran çıktısıyla
test edebilirsin:

```powershell
# Proje klasöründe:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r worker\requirements.txt

# 1) İlk tarama (yerel pcbildirim.db oluşur, ilk runda bildirim olmaz)
.\.venv\Scripts\python.exe -m worker.main

# 2) Çıkan modelleri gör (web önerileri bunlardan beslenir)
.\.venv\Scripts\python.exe -m worker.devtools list-models

# 3) Bir model filtresi ekle
.\.venv\Scripts\python.exe -m worker.devtools add-filter --label "RTX 5070" --model "RTX 5070" --threshold 0

# 4) Yapay fiyat düşüşü üret ve tekrar tara -> ekrana "BİLDİRİM" basmalı
.\.venv\Scripts\python.exe -m worker.devtools bump --like 5070 --pct 12
.\.venv\Scripts\python.exe -m worker.main
```

> Varsayılanlar: `STORE=sqlite`, `NOTIFY=console`. Hiçbir ortam değişkeni gerekmez.

---

## 2) Bulut kurulumu (7/24 çalışması için)

### a) Supabase (veritabanı)
1. [supabase.com](https://supabase.com) → ücretsiz proje aç.
2. **SQL Editor** → [`supabase/schema.sql`](supabase/schema.sql) içeriğinin tamamını
   yapıştır → **Run**.
3. **Project Settings → API**'den şunları not al:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → web için (`VITE_SUPABASE_ANON_KEY`)
   - `service_role` key → worker için (`SUPABASE_SERVICE_KEY`) — **gizli tut!**

### b) Telegram (bildirim)
1. Telegram'da **@BotFather** → `/newbot` → bot adı ver → **token**'ı al
   (`TELEGRAM_BOT_TOKEN`).
2. Oluşturduğun bota Telegram'dan herhangi bir mesaj at ("merhaba").
3. Tarayıcıda aç: `https://api.telegram.org/bot<TOKEN>/getUpdates` →
   gelen JSON'daki `chat.id` senin **chat id**'in. Bunu web arayüzündeki
   "Telegram bildirimi" kutusuna gir (veya Supabase `settings` tablosuna yaz).

### c) GitHub Actions (worker — 7/24 tarama)
1. Bu klasörü bir GitHub deposuna gönder. **Public repo öner** (özel repo'da aylık
   2000 dk Actions limiti var; public'te sınırsız). Kod sır içermez.
   ```powershell
   git init
   git add .
   git commit -m "PC Fırsat Bildirim"
   git branch -M main
   git remote add origin https://github.com/<kullanıcı>/<repo>.git
   git push -u origin main
   ```
   > Git kurulu değilse: https://git-scm.com/download/win
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**:
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TELEGRAM_BOT_TOKEN`.
3. Repo → **Actions** sekmesini etkinleştir. İş [`.github/workflows/check.yml`](.github/workflows/check.yml)
   ile her 20 dk'da çalışır; **Run workflow** ile elle de tetikleyebilirsin.

### d) Web arayüzü (Vercel veya Netlify — ücretsiz)
- **Root/Base directory:** `web`
- **Build command:** `npm run build` · **Output:** `dist`
- **Environment variables:**
  - `VITE_SUPABASE_URL` = Supabase Project URL
  - `VITE_SUPABASE_ANON_KEY` = anon public key
  - `VITE_APP_PASSWORD` = (opsiyonel) arayüze basit parola kapısı

Yerelde denemek için:
```powershell
cd web
copy .env.example .env.local   # içini doldur
npm install
npm run dev
```

---

## 3) Günlük kullanım
Web arayüzünden:
- **Model** seç (öneri listesi gerçek ürünlerden gelir) → "RTX 5070" gibi.
- İstersen **anahtar kelime** ("white"), **hariç** ("oem"), **maks. fiyat**,
  **düşüş eşiği** ve **site** ekle. → **Ekle**.
- "Eşleşenler" ile o an uyan ürünleri ve fiyatları gör.
- Ürün ucuzlayınca worker bir sonraki taramada Telegram'dan haber verir.

---

## 4) Daha fazla kategori ekleme
Varsayılan olarak sadece **ekran kartı** taranır. İşlemci, anakart, hazır sistem vb.
için [`worker/config.py`](worker/config.py) içindeki `ITOPYA_CATEGORIES` /
`INCEHESAP_CATEGORIES` listelerinde ilgili satırların yorumunu kaldır.

| Site | Sayfalama | Ürün/fiyat kaynağı |
|------|-----------|--------------------|
| itopya | `?pg=N` | `div.product` + `span.product-price` |
| incehesap | `/sayfa-N/` | `a.product[data-product]` JSON |

---

## Notlar / sınırlamalar
- **Nazik tarama:** her istek arası kısa bekleme var (`REQUEST_DELAY`). Çok sık tarama
  yapma; siteleri yorma.
- **IP engeli:** Actions veri merkezi IP'leri nadiren engellenebilir. Olursa worker'ı
  evde Windows Görev Zamanlayıcı ile de çalıştırabilirsin (`STORE=supabase`,
  `NOTIFY=telegram` ortam değişkenleriyle `python -m worker.main`).
- **Cron gecikmesi:** GitHub zamanlanmış işleri birkaç dk gecikebilir; repo 60 gün
  hareketsiz kalırsa cron durur (ara sıra elle "Run workflow").
- **Site HTML'i değişirse** scraper güncellenmeli; site modülleri
  [`worker/sites/`](worker/sites/) altında izole.
- **Güvenlik:** web `anon` key herkese açıktır; veriler hassas değil ama yine de
  `VITE_APP_PASSWORD` ile basit kapı koymanı öneririz. Daha güçlüsü için Supabase Auth.
