import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useSEO } from "../hooks/useSEO";

type Section = "profile"|"saved"|"viewings"|"alerts"|"settings"|"faq"|"support"|"privacy"|"terms"|"landlord";

const NAV_DEFS = [
  { id: "profile",  label: "Profile",           icon: "◍" },
  { id: "saved",    label: "Saved properties",   icon: "♥" },
  { id: "viewings", label: "Viewings",            icon: "▣" },
  { id: "alerts",   label: "Alerts",              icon: "◔" },
  { id: "settings", label: "Settings",            icon: "⚙" },
  { id: "faq",      label: "FAQ",                 icon: "?" },
  { id: "support",  label: "Support",             icon: "✉" },
  { id: "privacy",  label: "Privacy policy",      icon: "⛨" },
  { id: "terms",    label: "Terms & conditions",  icon: "▤" },
  { id: "landlord", label: "Landlord portal",     icon: "⌂", soon: true },
];

const TITLES: Record<Section, [string, string]> = {
  profile:  ["Profile",           "Manage your details and preferences."],
  saved:    ["Saved properties",  "3 properties saved."],
  viewings: ["Viewings",          "Your booked and requested viewings."],
  alerts:   ["Alerts",            "2 active alerts."],
  settings: ["Settings",          "Notifications, language and security."],
  faq:      ["FAQ",               "Answers to the questions we hear most."],
  support:  ["Support",           "We aim to respond within 24 hours."],
  privacy:  ["Privacy policy",    "How we handle your data."],
  terms:    ["Terms & conditions","The rules for using Ulouka."],
  landlord: ["Landlord portal",   "List your space directly on Ulouka."],
};

const FAQ = [
  { q: "How does Ulouka source its listings?", a: "We aggregate from 30+ sources including Rightmove, Zoopla, church bodies, auction houses, planning portals and the Charities Commission." },
  { q: "What does the match score mean?", a: "The score reflects suitability for your stated purpose — based on listing details, planning status, location and comparable transactions." },
  { q: "How do pre-market signals work?", a: "We monitor Charities Commission filings, Companies House dissolutions and planning applications. These can give 6–18 months advance notice before a property lists." },
  { q: "Is my data safe?", a: "Yes. AES-256 encryption, UK data centres, ICO registered. Export or delete your data at any time from your profile." },
  { q: "Can I get WhatsApp alerts?", a: "Yes — add your phone number in Profile and enable WhatsApp alerts in Settings." },
  { q: "What is a magic link?", a: "A one-time secure sign-in link sent to your email. No password required. Expires in 15 minutes, single use only." },
];

const PRIVACY = [
  { h: "What we collect", b: "Email address, name, search preferences and saved properties. We collect only what is necessary for the service." },
  { h: "How we use it", b: "To provide property search, alerts and match analysis. We do not sell your data or share it with advertisers." },
  { h: "Lawful basis", b: "Contract (your account), legitimate interest (improving the service) and consent (optional analytics). You can withdraw consent at any time." },
  { h: "Data retention", b: "Account data is kept while your account is active. Search history is retained for 90 days. Audit logs are kept for 7 years." },
  { h: "Your rights", b: "Access, rectification, erasure, portability and objection under UK GDPR. Contact privacy@ulouka.com." },
];

const TERMS = [
  { h: "Service description", b: "Ulouka aggregates publicly available property listings and provides match analysis. We are not an estate agent and do not act on your behalf in any transaction." },
  { h: "Analysis disclaimer", b: "Match scores are indicative only. They do not constitute professional property, legal or financial advice. Always instruct qualified professionals before purchasing." },
  { h: "Data accuracy", b: "Listing data is sourced from third parties. We cannot guarantee accuracy or availability. Always verify directly with the source." },
  { h: "Acceptable use", b: "You may not scrape, automate or resell data from Ulouka. The service is for personal property search only." },
  { h: "Governing law", b: "These terms are governed by English law. Disputes are subject to the exclusive jurisdiction of English courts." },
];

const row = (label: string, value?: string, action?: string, danger?: boolean) => ({
  label, value, action, danger: !!danger,
  hasValue: !!value,
  labelColor: danger ? "#c0392b" : "var(--ink)",
  actionColor: danger ? "#c0392b" : "var(--ink3)",
});

const PROFILE_CARDS = [
  { rows: [row("Full name","Alex Mercer","Edit"), row("Email","alex@ulouka.co.uk","Change"), row("Phone","Not set","Add"), row("Password","••••••••••••","Change")] },
  { rows: [row("Search intent","Conversion to a home","Edit"), row("Max budget","£250,000","Edit"), row("Preferred counties","Yorkshire, Lancashire","Edit")] },
  { rows: [row("Export my data",undefined,"Download JSON"), row("Delete account",undefined,"Delete",true)] },
];

const SETTINGS_CARDS = [
  { rows: [row("Email notifications","Enabled","Toggle"), row("WhatsApp alerts","Disabled","Toggle"), row("Weekly digest","Monday mornings","Edit"), row("Alert frequency","Immediate","Edit")] },
  { rows: [row("Language","English (UK)","Change"), row("Currency","GBP £","Change")] },
  { rows: [row("Two-factor authentication","Not enabled","Enable"), row("Active sessions","1 session","View all"), row("Sign out all devices",undefined,"Sign out",true)] },
];

const SAVED = [
  { title: "St. Mark's Methodist Chapel", meta: "Halifax, West Yorkshire · £165,000" },
  { title: "Wesleyan Chapel & Hall",       meta: "Barnsley, South Yorkshire · £119,000" },
  { title: "Bethel Chapel",                meta: "Treorchy, Mid Glamorgan · £78,000" },
];

const SUPPORT = [
  { label: "Email support",   value: "support@ulouka.co.uk",    action: "Open email" },
  { label: "Report a bug",    value: "Something not working?", action: "Report" },
  { label: "Feature request", value: "Suggest something new",  action: "Suggest" },
];

const SIMPLE: Record<string, { icon: string; title: string; body: string; cta: string; href: string }> = {
  viewings: { icon: "▣", title: "No viewings booked yet",  body: "When you request viewings through Ulouka, they'll appear here.", cta: "Browse properties", href: "/" },
  alerts:   { icon: "◔", title: "2 active alerts",          body: "Manage the alerts that notify you when matching properties appear.", cta: "Go to alerts", href: "/alerts" },
  landlord: { icon: "⌂", title: "Coming soon",              body: "List your church or gathering space directly on Ulouka. Reach verified buyers and track interest in real time.", cta: "Join the waitlist", href: "/account" },
};

const s: React.CSSProperties = {};

export default function AccountPage() {
 useSEO({ title: "Account — Ulouka", description: "Manage your Ulouka account, saved searches, and preferences." });
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [active, setActive] = useState<Section>("profile");
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const name = user?.name || "N";
  const initial = name.charAt(0).toUpperCase();
  const [title, sub] = TITLES[active];

  const isText   = active === "privacy" || active === "terms";
  const isSimple = active === "viewings" || active === "alerts" || active === "landlord";
  const textItems = active === "terms" ? TERMS : PRIVACY;
  const simple = SIMPLE[active] || SIMPLE.viewings;

  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "50px 22px 90px", display: "grid", gridTemplateColumns: "240px 1fr", gap: 48, alignItems: "start", animation: "riseIn .6s cubic-bezier(.16,1,.3,1) both" }}>

      {/* Sidebar */}
      <aside style={{ position: "sticky", top: 74 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, paddingBottom: 20, marginBottom: 18, borderBottom: "1px solid var(--line)" }}>
          <span style={{ width: 42, height: 42, borderRadius: "50%", background: "var(--btnbg)", color: "var(--btnfg)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Gabarito'", fontWeight: 800, fontSize: 17, flexShrink: 0 }}>{initial}</span>
          <div style={{ minWidth: 0 }}>
            <p style={{ font: "600 14px 'Space Grotesk'", color: "var(--ink)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</p>
            <p style={{ font: "400 12px 'Space Grotesk'", color: "var(--ink3)", margin: "2px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.email || ""}</p>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {NAV_DEFS.map(n => {
            const isActive = n.id === active;
            return (
              <button key={n.id}
                onClick={() => { if (!n.soon) setActive(n.id as Section); }}
                style={{ display: "flex", alignItems: "center", gap: 11, width: "100%", padding: "9px 12px", borderRadius: 11, border: "none", background: isActive ? "var(--btnbg)" : "transparent", color: isActive ? "var(--btnfg)" : n.soon ? "var(--ink3)" : "var(--ink)", font: `${isActive ? 600 : 400} 13px 'Space Grotesk'`, cursor: n.soon ? "default" : "pointer", textAlign: "left" }}
              >
                <span style={{ fontSize: 13, width: 15, textAlign: "center", flexShrink: 0, opacity: 0.85 }}>{n.icon}</span>
                {n.label}
                {n.soon && <span style={{ marginLeft: "auto", font: "500 9px 'Space Grotesk'", letterSpacing: "0.06em", textTransform: "uppercase", background: "var(--surface2)", color: "var(--ink3)", padding: "2px 6px", borderRadius: 5 }}>Soon</span>}
              </button>
            );
          })}
          <button onClick={() => { logout(); navigate("/"); }} style={{ display: "flex", alignItems: "center", gap: 11, width: "100%", padding: "9px 12px", borderRadius: 11, border: "none", background: "transparent", color: "#c0392b", font: "400 13px 'Space Grotesk'", cursor: "pointer", textAlign: "left", marginTop: 6 }}>
            <span style={{ width: 15, textAlign: "center", flexShrink: 0 }}>⏻</span>Log out
          </button>
        </div>
      </aside>

      {/* Content */}
      <section style={{ minWidth: 0 }}>
        <h1 style={{ fontFamily: "'Gabarito'", fontWeight: 900, fontSize: 32, letterSpacing: "-0.03em", color: "var(--ink)", margin: "0 0 6px" }}>{title}</h1>
        <p style={{ font: "300 16px 'Space Grotesk'", color: "var(--ink2)", margin: "0 0 28px" }}>{sub}</p>

        {/* PROFILE */}
        {active === "profile" && (
          <div style={{ animation: "riseIn .35s ease both" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 28 }}>
              <span style={{ width: 60, height: 60, borderRadius: "50%", background: "var(--btnbg)", color: "var(--btnfg)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Gabarito'", fontWeight: 800, fontSize: 24 }}>{initial}</span>
              <div>
                <p style={{ font: "600 17px 'Space Grotesk'", color: "var(--ink)", margin: 0 }}>{name}</p>
                <p style={{ font: "400 14px 'Space Grotesk'", color: "var(--ink3)", margin: "3px 0 0" }}>{user?.email || ""}</p>
              </div>
            </div>
            {PROFILE_CARDS.map((card, ci) => (
              <div key={ci} style={{ border: "1px solid var(--line)", borderRadius: 18, background: "var(--surface)", padding: "4px 22px", marginBottom: 16 }}>
                {card.rows.map((r, ri) => (
                  <div key={ri} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "15px 0", borderBottom: "1px solid var(--line3)" }}>
                    <div>
                      <p style={{ font: "500 14px 'Space Grotesk'", color: r.labelColor, margin: 0 }}>{r.label}</p>
                      {r.hasValue && <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "3px 0 0" }}>{r.value}</p>}
                    </div>
                    <span style={{ font: "400 13px 'Space Grotesk'", color: r.actionColor, whiteSpace: "nowrap", cursor: "pointer" }}>{r.action} ›</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* SAVED */}
        {active === "saved" && (
          <div style={{ animation: "riseIn .35s ease both", display: "flex", flexDirection: "column", gap: 10 }}>
            {SAVED.map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, border: "1px solid var(--line)", borderRadius: 16, background: "var(--surface)", padding: "16px 20px" }}>
                <div>
                  <p style={{ font: "600 15px 'Space Grotesk'", color: "var(--ink)", margin: 0 }}>{s.title}</p>
                  <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "3px 0 0" }}>{s.meta}</p>
                </div>
                <span style={{ color: "var(--ink3)", fontSize: 16 }}>›</span>
              </div>
            ))}
          </div>
        )}

        {/* SETTINGS */}
        {active === "settings" && (
          <div style={{ animation: "riseIn .35s ease both" }}>
            {SETTINGS_CARDS.map((card, ci) => (
              <div key={ci} style={{ border: "1px solid var(--line)", borderRadius: 18, background: "var(--surface)", padding: "4px 22px", marginBottom: 16 }}>
                {card.rows.map((r, ri) => (
                  <div key={ri} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "15px 0", borderBottom: "1px solid var(--line3)" }}>
                    <div>
                      <p style={{ font: "500 14px 'Space Grotesk'", color: r.labelColor, margin: 0 }}>{r.label}</p>
                      {r.hasValue && <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "3px 0 0" }}>{r.value}</p>}
                    </div>
                    <span style={{ font: "400 13px 'Space Grotesk'", color: r.actionColor, whiteSpace: "nowrap", cursor: "pointer" }}>{r.action} ›</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* FAQ */}
        {active === "faq" && (
          <div style={{ animation: "riseIn .35s ease both", border: "1px solid var(--line)", borderRadius: 18, background: "var(--surface)", padding: "6px 24px" }}>
            {FAQ.map((q, i) => (
              <div key={i} style={{ borderBottom: "1px solid var(--line3)", padding: "16px 0" }}>
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)} style={{ font: "600 15px 'Space Grotesk'", color: "var(--ink)", cursor: "pointer", background: "none", border: "none", width: "100%", textAlign: "left", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: 0 }}>
                  {q.q}<span style={{ color: "var(--ink3)", fontSize: 15 }}>{openFaq === i ? "−" : "+"}</span>
                </button>
                {openFaq === i && <p style={{ font: "300 14px/1.65 'Space Grotesk'", color: "var(--ink2)", margin: "12px 0 0" }}>{q.a}</p>}
              </div>
            ))}
          </div>
        )}

        {/* SUPPORT */}
        {active === "support" && (
          <div style={{ animation: "riseIn .35s ease both", display: "flex", flexDirection: "column", gap: 10 }}>
            {SUPPORT.map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, border: "1px solid var(--line)", borderRadius: 16, background: "var(--surface)", padding: "18px 20px" }}>
                <div>
                  <p style={{ font: "600 15px 'Space Grotesk'", color: "var(--ink)", margin: 0 }}>{s.label}</p>
                  <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "3px 0 0" }}>{s.value}</p>
                </div>
                <span style={{ font: "500 13px 'Space Grotesk'", color: "#6b70c2", whiteSpace: "nowrap", cursor: "pointer" }}>{s.action} →</span>
              </div>
            ))}
          </div>
        )}

        {/* PRIVACY / TERMS */}
        {isText && (
          <div style={{ animation: "riseIn .35s ease both", maxWidth: 620 }}>
            <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "0 0 22px" }}>Last updated · June 2026</p>
            {textItems.map((t, i) => (
              <div key={i} style={{ marginBottom: 22 }}>
                <p style={{ font: "600 15px 'Space Grotesk'", color: "var(--ink)", margin: "0 0 5px" }}>{t.h}</p>
                <p style={{ font: "300 14px/1.7 'Space Grotesk'", color: "var(--ink2)", margin: 0 }}>{t.b}</p>
              </div>
            ))}
          </div>
        )}

        {/* SIMPLE (viewings/alerts/landlord) */}
        {isSimple && (
          <div style={{ animation: "riseIn .35s ease both", border: "1px solid var(--line)", borderRadius: 22, background: "var(--surface)", padding: "52px 32px", textAlign: "center" }}>
            <div style={{ width: 58, height: 58, borderRadius: "50%", background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 18px", fontSize: 24, color: "var(--ink3)" }}>{simple.icon}</div>
            <p style={{ fontFamily: "'Gabarito'", fontWeight: 700, fontSize: 18, color: "var(--ink)", margin: "0 0 8px" }}>{simple.title}</p>
            <p style={{ font: "300 15px/1.6 'Space Grotesk'", color: "var(--ink2)", margin: "0 auto 22px", maxWidth: 340 }}>{simple.body}</p>
            <button onClick={() => navigate(simple.href)} style={{ display: "inline-block", background: "var(--btnbg)", color: "var(--btnfg)", borderRadius: 980, padding: "11px 24px", font: "500 14px 'Space Grotesk'", border: "none", cursor: "pointer" }}>{simple.cta}</button>
          </div>
        )}
      </section>
    </main>
  );
}
