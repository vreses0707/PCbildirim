import { useEffect, useMemo, useState } from "react";
import { supabase, isConfigured } from "./supabaseClient.js";

const SITES = ["itopya", "incehesap"];

function tl(n) {
  if (n == null) return "-";
  return Number(n).toLocaleString("tr-TR") + " TL";
}
function splitCsv(s) {
  return (s || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

// ----------------------------- Parola kapısı -----------------------------
function Gate({ children }) {
  const pass = import.meta.env.VITE_APP_PASSWORD;
  const [ok, setOk] = useState(!pass || sessionStorage.getItem("unlocked") === "1");
  const [val, setVal] = useState("");
  if (ok) return children;
  return (
    <div className="center">
      <form
        className="card narrow"
        onSubmit={(e) => {
          e.preventDefault();
          if (val === pass) {
            sessionStorage.setItem("unlocked", "1");
            setOk(true);
          } else alert("Parola yanlış");
        }}
      >
        <h2>🔒 Giriş</h2>
        <input
          type="password"
          placeholder="Parola"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          autoFocus
        />
        <button type="submit">Gir</button>
      </form>
    </div>
  );
}

// ----------------------------- Filtre formu -----------------------------
function FilterForm({ models, onAdded }) {
  const empty = {
    model: "",
    keywords: "",
    exclude_keywords: "",
    sites: [],
    max_price: "",
    drop_threshold_pct: 2,
  };
  const [f, setF] = useState(empty);
  const [busy, setBusy] = useState(false);

  const label = useMemo(() => {
    const parts = [f.model || splitCsv(f.keywords).join(" ")].filter(Boolean);
    if (f.max_price) parts.push(`< ${tl(f.max_price)}`);
    return parts.join("  ") || "Yeni filtre";
  }, [f]);

  function toggleSite(s) {
    setF((p) => ({
      ...p,
      sites: p.sites.includes(s) ? p.sites.filter((x) => x !== s) : [...p.sites, s],
    }));
  }

  async function submit(e) {
    e.preventDefault();
    if (!f.model && !splitCsv(f.keywords).length) {
      alert("En az bir model seç ya da anahtar kelime gir.");
      return;
    }
    setBusy(true);
    const row = {
      label,
      model: f.model || null,
      keywords: splitCsv(f.keywords),
      exclude_keywords: splitCsv(f.exclude_keywords),
      sites: f.sites,
      max_price: f.max_price ? Number(f.max_price) : null,
      drop_threshold_pct: Number(f.drop_threshold_pct) || 0,
      active: true,
    };
    const { error } = await supabase.from("filters").insert(row);
    setBusy(false);
    if (error) return alert("Hata: " + error.message);
    setF(empty);
    onAdded();
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>➕ Yeni takip filtresi</h2>

      <label>Model (öneri listesinden)</label>
      <select value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })}>
        <option value="">— Model seçme (anahtar kelime kullan) —</option>
        {models.map((m) => (
          <option key={m.model} value={m.model}>
            {m.model} · {m.product_count} ürün · en ucuz {tl(m.min_price)}
          </option>
        ))}
      </select>
      <p className="hint">
        Model seçersen tam eşleşir: "RTX 5070" seçince "RTX 5070 Ti" gelmez.
      </p>

      <label>Anahtar kelimeler (virgülle) — opsiyonel</label>
      <input
        placeholder="örn: white, ASUS"
        value={f.keywords}
        onChange={(e) => setF({ ...f, keywords: e.target.value })}
      />

      <label>Hariç tutulacaklar (virgülle) — opsiyonel</label>
      <input
        placeholder="örn: ti, oem"
        value={f.exclude_keywords}
        onChange={(e) => setF({ ...f, exclude_keywords: e.target.value })}
      />

      <div className="row">
        <div>
          <label>Maks. fiyat (TL) — opsiyonel</label>
          <input
            type="number"
            placeholder="örn: 40000"
            value={f.max_price}
            onChange={(e) => setF({ ...f, max_price: e.target.value })}
          />
        </div>
        <div>
          <label>Düşüş eşiği (%)</label>
          <input
            type="number"
            step="0.5"
            value={f.drop_threshold_pct}
            onChange={(e) => setF({ ...f, drop_threshold_pct: e.target.value })}
          />
        </div>
      </div>

      <label>Siteler (boş = ikisi de)</label>
      <div className="chips">
        {SITES.map((s) => (
          <button
            type="button"
            key={s}
            className={"chip" + (f.sites.includes(s) ? " on" : "")}
            onClick={() => toggleSite(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <button type="submit" disabled={busy} className="primary">
        {busy ? "Ekleniyor…" : `Ekle:  ${label}`}
      </button>
    </form>
  );
}

// --------------------------- Eşleşen ürünler ---------------------------
function Matches({ filter }) {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    let q = supabase.from("products").select("site,name,model,current_price,url");
    if (filter.model) q = q.eq("model", filter.model);
    for (const kw of filter.keywords || []) q = q.ilike("name", `%${kw}%`);
    if (filter.max_price) q = q.lte("current_price", filter.max_price);
    if (filter.sites?.length) q = q.in("site", filter.sites);
    q.order("current_price").limit(50).then(({ data }) => {
      let r = data || [];
      for (const ex of filter.exclude_keywords || [])
        r = r.filter((p) => !p.name.toLowerCase().includes(ex.toLowerCase()));
      setRows(r);
    });
  }, [filter]);

  if (rows == null) return <p className="hint">Yükleniyor…</p>;
  if (!rows.length) return <p className="hint">Şu an eşleşen ürün yok.</p>;
  return (
    <table className="matches">
      <tbody>
        {rows.map((p) => (
          <tr key={p.url}>
            <td className="price">{tl(p.current_price)}</td>
            <td className="site">{p.site}</td>
            <td>
              <a href={p.url} target="_blank" rel="noreferrer">
                {p.name}
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ----------------------------- Filtre listesi -----------------------------
function FilterList({ filters, reload }) {
  const [openId, setOpenId] = useState(null);

  async function toggle(f) {
    await supabase.from("filters").update({ active: !f.active }).eq("id", f.id);
    reload();
  }
  async function remove(f) {
    if (!confirm(`Silinsin mi: ${f.label}?`)) return;
    await supabase.from("filters").delete().eq("id", f.id);
    reload();
  }

  if (!filters.length)
    return <p className="hint">Henüz filtre yok. Yukarıdan ekle 👆</p>;

  return (
    <div className="list">
      {filters.map((f) => (
        <div className={"card filter" + (f.active ? "" : " off")} key={f.id}>
          <div className="filter-head">
            <div>
              <strong>{f.label}</strong>
              <div className="meta">
                {f.model && <span className="tag">model: {f.model}</span>}
                {(f.keywords || []).map((k) => (
                  <span className="tag" key={k}>
                    {k}
                  </span>
                ))}
                {(f.exclude_keywords || []).map((k) => (
                  <span className="tag ex" key={k}>
                    −{k}
                  </span>
                ))}
                {f.max_price && <span className="tag">≤ {tl(f.max_price)}</span>}
                <span className="tag">eşik %{f.drop_threshold_pct}</span>
                {f.sites?.length ? (
                  <span className="tag">{f.sites.join(", ")}</span>
                ) : (
                  <span className="tag">tüm siteler</span>
                )}
              </div>
            </div>
            <div className="actions">
              <button onClick={() => setOpenId(openId === f.id ? null : f.id)}>
                {openId === f.id ? "Gizle" : "Eşleşenler"}
              </button>
              <button onClick={() => toggle(f)}>{f.active ? "Duraklat" : "Aktif et"}</button>
              <button className="danger" onClick={() => remove(f)}>
                Sil
              </button>
            </div>
          </div>
          {openId === f.id && <Matches filter={f} />}
        </div>
      ))}
    </div>
  );
}

// ----------------------------- Telegram ayarı -----------------------------
function Settings() {
  const [chatId, setChatId] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    supabase
      .from("settings")
      .select("telegram_chat_id")
      .eq("id", 1)
      .single()
      .then(({ data }) => setChatId(data?.telegram_chat_id || ""));
  }, []);
  async function save() {
    const { error } = await supabase
      .from("settings")
      .update({ telegram_chat_id: chatId || null })
      .eq("id", 1);
    if (error) return alert("Hata: " + error.message);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }
  return (
    <div className="card">
      <h2>📨 Telegram bildirimi</h2>
      <p className="hint">
        Bildirimlerin gideceği Telegram sohbet kimliği (chat id). Almak için: botuna
        Telegram'dan bir mesaj at, sonra{" "}
        <code>https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code> adresindeki{" "}
        <code>chat.id</code> değerini buraya yaz.
      </p>
      <div className="row">
        <input
          placeholder="örn: 123456789"
          value={chatId}
          onChange={(e) => setChatId(e.target.value)}
        />
        <button className="primary" onClick={save}>
          {saved ? "Kaydedildi ✓" : "Kaydet"}
        </button>
      </div>
    </div>
  );
}

// --------------------------------- App ---------------------------------
export default function App() {
  const [filters, setFilters] = useState([]);
  const [models, setModels] = useState([]);

  async function reload() {
    const { data } = await supabase
      .from("filters")
      .select("*")
      .order("created_at", { ascending: false });
    setFilters(data || []);
  }
  async function loadModels() {
    const { data } = await supabase
      .from("catalog_models")
      .select("*")
      .order("product_count", { ascending: false });
    setModels(data || []);
  }

  useEffect(() => {
    if (isConfigured) {
      reload();
      loadModels();
    }
  }, []);

  if (!isConfigured) {
    return (
      <div className="center">
        <div className="card narrow">
          <h2>⚙️ Yapılandırma gerekli</h2>
          <p>
            <code>web/.env.local</code> dosyasına Supabase bilgilerini gir
            (<code>.env.example</code>'a bak), sonra sayfayı yenile.
          </p>
        </div>
      </div>
    );
  }

  return (
    <Gate>
      <div className="app">
        <header>
          <h1>🖥️ PC Fırsat Bildirim</h1>
          <p>itopya & incehesap'ta takip ettiğin ürünler ucuzlayınca Telegram'dan haber al.</p>
        </header>
        <div className="grid">
          <div>
            <FilterForm models={models} onAdded={reload} />
            <Settings />
          </div>
          <div>
            <h2 className="section">📋 Filtrelerin ({filters.length})</h2>
            <FilterList filters={filters} reload={reload} />
          </div>
        </div>
      </div>
    </Gate>
  );
}
