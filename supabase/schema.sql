-- PC Fırsat Bildirim — Supabase (Postgres) şeması
-- Supabase panelinde: SQL Editor -> bu dosyanın tamamını yapıştır -> Run.
-- Worker SERVICE key ile bağlanır (RLS'i baypas eder). Web ANON key ile bağlanır
-- ve aşağıdaki RLS politikalarıyla sınırlanır.

-- ============================ TABLOLAR ============================

create table if not exists products (
    url           text primary key,
    site          text,
    name          text,
    category      text,
    brand         text,
    model         text,
    image         text,
    current_price numeric,
    last_seen_at  timestamptz default now()
);

create table if not exists price_history (
    id          bigint generated always as identity primary key,
    product_url text references products(url) on delete cascade,
    price       numeric,
    seen_at     timestamptz default now()
);
create index if not exists idx_price_history_url on price_history(product_url);

create table if not exists filters (
    id                 bigint generated always as identity primary key,
    label              text,
    keywords           text[] default '{}',
    exclude_keywords   text[] default '{}',
    sites              text[] default '{}',  -- boş = tüm siteler
    category           text,
    model              text,                  -- normalize model (örn. 'RTX 5070') -> tam eşleşme
    max_price          numeric,
    drop_threshold_pct numeric default 2,
    active             boolean default true,
    created_at         timestamptz default now()
);

create table if not exists alerts (
    id          bigint generated always as identity primary key,
    product_url text,
    filter_id   bigint,
    old_price   numeric,
    new_price   numeric,
    sent_at     timestamptz default now()
);
create index if not exists idx_alerts_dedup on alerts(product_url, filter_id, new_price);

create table if not exists settings (
    id               int primary key check (id = 1),
    telegram_chat_id text
);
insert into settings (id, telegram_chat_id) values (1, null)
    on conflict (id) do nothing;

-- =================== ÖNERİ KATALOĞU (web için) ===================
-- Web arayüzünün model/marka önerilerini hızlı çekmesi için görünüm.
create or replace view catalog_models as
    select model, count(*) as product_count, min(current_price) as min_price
    from products
    where model is not null
    group by model
    order by product_count desc;

-- ============================ RLS ============================
-- Kişisel kullanım için pratik kurulum: ürün/geçmiş/uyarı verisi herkese OKUNUR
-- (hassas değil); filtre ve ayarları web (anon) yönetebilir.
-- NOT: anon key herkese açıktır. Web tarafına basit bir parola kapısı koymanı öneririz.
-- Daha güçlü güvenlik için Supabase Auth'u açıp politikaları auth.uid() ile sınırla.

alter table products      enable row level security;
alter table price_history enable row level security;
alter table filters       enable row level security;
alter table alerts        enable row level security;
alter table settings      enable row level security;

-- Salt okunur tablolar (anon select)
create policy "read products"      on products      for select using (true);
create policy "read price_history" on price_history for select using (true);
create policy "read alerts"        on alerts        for select using (true);

-- Filtreler: anon tam yönetim (oku/ekle/güncelle/sil)
create policy "manage filters select" on filters for select using (true);
create policy "manage filters insert" on filters for insert with check (true);
create policy "manage filters update" on filters for update using (true) with check (true);
create policy "manage filters delete" on filters for delete using (true);

-- Ayarlar: anon oku/güncelle (telegram_chat_id girmek için)
create policy "read settings"   on settings for select using (true);
create policy "update settings" on settings for update using (true) with check (true);
