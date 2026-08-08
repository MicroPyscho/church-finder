import { useState } from "react";
import { useAuthStore } from "../stores/authStore";

interface Alert {
  id: number;
  name: string;
  meta: string;
}

export default function AlertsPage() {
  const { user } = useAuthStore();
  const [alerts, setAlerts] = useState<Alert[]>([
    { id: 1, name: "Yorkshire chapels under £200k", meta: "Keywords: methodist chapel hall · Max £200,000 · Counties: West & South Yorkshire" },
    { id: 2, name: "Listed churches to convert", meta: "Keywords: grade listed conversion · Min match 75% · Counties: All UK" },
  ]);
  const [form, setForm] = useState({ name: "", query: "", max_price: "", counties: "", min_ai_score: "" });
  const [justSaved, setJustSaved] = useState(false);
  const [nextId, setNextId] = useState(3);

  function setField(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  function createAlert() {
    const name = form.name.trim() || form.query.trim() || "New alert";
    const bits: string[] = [];
    if (form.query.trim()) bits.push("Keywords: " + form.query.trim());
    if (form.max_price.trim()) { const n = Number(form.max_price.replace(/[^0-9]/g, "")); if (n) bits.push("Max £" + n.toLocaleString()); }
    if (form.counties.trim()) bits.push("Counties: " + form.counties.trim());
    if (form.min_ai_score.trim()) bits.push("Min match " + form.min_ai_score + "%");
    const meta = bits.length ? bits.join(" · ") : "All churches, chapels & places of worship";
    setAlerts(a => [{ id: nextId, name, meta }, ...a]);
    setNextId(n => n + 1);
    setForm({ name: "", query: "", max_price: "", counties: "", min_ai_score: "" });
    setJustSaved(true);
    setTimeout(() => setJustSaved(false), 2400);
  }

  function removeAlert(id: number) { setAlerts(a => a.filter(x => x.id !== id)); }

  const fields = [
    { k: "name", label: "Alert name", placeholder: "e.g. Churches under £200k, Kent", span: "1 / -1" },
    { k: "query", label: "Search keywords", placeholder: "e.g. former methodist chapel", span: "1 / -1" },
    { k: "max_price", label: "Max price (£)", placeholder: "e.g. 250,000", span: "auto" },
    { k: "min_ai_score", label: "Min match score (%)", placeholder: "e.g. 80", span: "auto" },
    { k: "counties", label: "Counties (comma-separated)", placeholder: "e.g. Kent, Surrey, Essex", span: "1 / -1" },
  ];

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "72px 22px 90px", animation: "riseIn .6s cubic-bezier(.16,1,.3,1) both" }}>
      <p style={{ font: "500 12px 'Space Grotesk'", letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink3)", margin: "0 0 16px" }}>Stay ahead of the market</p>
      <h1 style={{ fontFamily: "'Gabarito'", fontWeight: 900, fontSize: "clamp(36px,5.2vw,54px)", lineHeight: 1.0, letterSpacing: "-0.04em", color: "var(--ink)", margin: 0 }}>Alerts</h1>
      <p style={{ font: "300 19px/1.5 'Space Grotesk'", color: "var(--ink2)", margin: "18px 0 0", maxWidth: 520 }}>We'll notify you the moment a property matching your criteria appears across any of our sources.</p>

      {/* New alert form */}
      <div style={{ marginTop: 40, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 24, padding: "30px 30px 28px", boxShadow: "0 14px 50px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 22 }}>
          <span style={{ width: 30, height: 30, borderRadius: "50%", background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink)", fontSize: 17 }}>+</span>
          <h2 style={{ fontFamily: "'Gabarito'", fontWeight: 700, fontSize: 18, letterSpacing: "-0.01em", color: "var(--ink)", margin: 0 }}>New alert</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {fields.map(f => (
            <label key={f.k} style={{ display: "flex", flexDirection: "column", gap: 7, gridColumn: f.span }}>
              <span style={{ font: "500 12px 'Space Grotesk'", letterSpacing: "0.02em", color: "var(--ink2)" }}>{f.label}</span>
              <input
                value={(form as any)[f.k]}
                onChange={e => setField(f.k, e.target.value)}
                placeholder={f.placeholder}
                style={{ border: "1px solid var(--border)", borderRadius: 13, background: "var(--surface2)", padding: "12px 14px", font: "400 15px 'Space Grotesk'", color: "var(--ink)", outline: "none", width: "100%" }}
              />
            </label>
          ))}
        </div>
        <button
          onClick={createAlert}
          style={{ marginTop: 22, display: "inline-flex", alignItems: "center", gap: 8, background: "var(--btnbg)", color: "var(--btnfg)", border: "none", borderRadius: 980, padding: "13px 26px", font: "500 15px 'Space Grotesk'", cursor: "pointer" }}
        >
          {justSaved ? "✓ Alert created" : "Create alert"}
        </button>
      </div>

      {/* Active alerts */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, margin: "46px 0 18px" }}>
        <h2 style={{ fontFamily: "'Gabarito'", fontWeight: 700, fontSize: 17, color: "var(--ink)", margin: 0 }}>Active alerts</h2>
        <span style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink4)" }}>{alerts.length}</span>
        <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
      </div>

      {alerts.length === 0 && (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--ink3)" }}>
          <div style={{ width: 52, height: 52, borderRadius: "50%", background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px", fontSize: 22 }}>◔</div>
          <p style={{ font: "400 15px 'Space Grotesk'", margin: 0 }}>No alerts yet — create one above.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {alerts.map(a => (
          <div key={a.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 18, padding: "18px 22px" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 5 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#1a7a3c", display: "inline-block", boxShadow: "0 0 0 3px rgba(26,122,60,0.15)" }} />
                <span style={{ fontFamily: "'Gabarito'", fontWeight: 700, fontSize: 16, color: "var(--ink)" }}>{a.name}</span>
              </div>
              <p style={{ font: "400 13px/1.5 'Space Grotesk'", color: "var(--ink2)", margin: 0 }}>{a.meta}</p>
            </div>
            <button
              onClick={() => removeAlert(a.id)}
              style={{ flexShrink: 0, display: "inline-flex", alignItems: "center", gap: 6, background: "var(--surface2)", border: "1px solid var(--border2)", borderRadius: 980, padding: "8px 15px", font: "500 12px 'Space Grotesk'", color: "var(--ink2)", cursor: "pointer" }}
            >Remove</button>
          </div>
        ))}
      </div>
    </main>
  );
}
