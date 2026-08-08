import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  User, Heart, Calendar, Bell, Settings,
  HelpCircle, Shield, FileText, LogOut,
  ChevronRight, ChevronLeft, Building2, Mail
} from "lucide-react";
import { authApi, favouritesApi, alertsApi } from "../api/client";

/* ── Shared sub-page shell ───────────────────────────────────────────────── */
function SubPage({ title, onBack, children }: {
  title: string;
  onBack: () => void;
  children: React.ReactNode;
}) {
  return (
    <div>
      <button
        onClick={onBack}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          fontFamily: "var(--font-body)", fontSize: "0.82rem",
          color: "var(--mid)", background: "none", border: "none",
          cursor: "pointer", padding: "0 0 20px", transition: "color .13s",
        }}
      >
        <ChevronLeft size={15} /> Back
      </button>
      <h2 style={{
        fontFamily: "var(--font-display)",
        fontSize: "1.5rem", fontWeight: 900,
        letterSpacing: "-.03em", color: "var(--ink)",
        marginBottom: 24,
      }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

/* ── Reusable row ────────────────────────────────────────────────────────── */
function Row({ label, value, action, danger, onClick }: {
  label: string; value?: string; action?: string;
  danger?: boolean; onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 0", borderBottom: "1px solid var(--rule-soft)",
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <div>
        <p style={{ fontSize: "0.85rem", fontWeight: 500, color: danger ? "var(--red)" : "var(--ink)" }}>
          {label}
        </p>
        {value && (
          <p style={{ fontSize: "0.76rem", color: "var(--mid)", marginTop: 2 }}>{value}</p>
        )}
      </div>
      {action && (
        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.76rem", color: danger ? "var(--red)" : "var(--mid)" }}>
          {action} <ChevronRight size={12} />
        </div>
      )}
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      border: "1px solid var(--rule)", borderRadius: 8,
      padding: "4px 20px", marginBottom: 20, background: "var(--white)",
    }}>
      {children}
    </div>
  );
}

/* ── Nav items ───────────────────────────────────────────────────────────── */
const NAV = [
  { id: "profile",  label: "Profile",            icon: User       },
  { id: "saved",    label: "Saved properties",    icon: Heart      },
  { id: "viewings", label: "Viewings",            icon: Calendar   },
  { id: "alerts",   label: "Alerts",              icon: Bell       },
  { id: "settings", label: "Settings",            icon: Settings   },
  { id: "faq",      label: "FAQ",                 icon: HelpCircle },
  { id: "support",  label: "Support",             icon: Mail       },
  { id: "privacy",  label: "Privacy policy",      icon: Shield     },
  { id: "terms",    label: "Terms & conditions",  icon: FileText   },
  { id: "landlord", label: "Landlord portal",     icon: Building2, soon: true },
];

/* ── Section content ─────────────────────────────────────────────────────── */
function ProfileSection({ user, logout }: { user: any; logout: () => void }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 28 }}>
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: "var(--ink)", color: "var(--white)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--font-display)", fontSize: "1.3rem", fontWeight: 900,
        }}>
          {user?.full_name?.[0]?.toUpperCase() ?? "?"}
        </div>
        <div>
          <p style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--ink)" }}>{user?.full_name || "—"}</p>
          <p style={{ fontSize: "0.78rem", color: "var(--mid)" }}>{user?.email}</p>
          {!user?.is_verified && (
            <p style={{ fontSize: "0.72rem", color: "var(--orange)", marginTop: 2 }}>Email not verified</p>
          )}
        </div>
      </div>
      <Card>
        <Row label="Full name" value={user?.full_name || "Not set"} action="Edit" />
        <Row label="Email"     value={user?.email}                  action="Change" />
        <Row label="Phone"     value="Not set"                      action="Add" />
        <Row label="Password"  value="••••••••••••"                 action="Change" />
      </Card>
      <Card>
        <Row label="Search intent"      value={user?.intent || "Not set"} action="Edit" />
        <Row label="Max budget"         value={user?.max_budget ? "£" + user.max_budget.toLocaleString() : "Not set"} action="Edit" />
        <Row label="Preferred counties" value="Not set" action="Edit" />
      </Card>
      <Card>
        <Row label="Export my data" action="Download JSON" onClick={() => {}} />
        <Row label="Delete account" action="Delete" danger onClick={() => {
          if (confirm("This will permanently delete your account and all data. Cannot be undone.")) logout();
        }} />
      </Card>
    </div>
  );
}

function SavedSection({ favs, navigate }: { favs: any[]; navigate: (s: string) => void }) {
  return (
    <div>
      <p style={{ fontSize: "0.85rem", color: "var(--mid)", marginBottom: 20 }}>
        {favs?.length ?? 0} properties saved
      </p>
      {!favs?.length ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "var(--mid)" }}>
          <Heart size={28} strokeWidth={1} style={{ margin: "0 auto 12px" }} />
          <p style={{ fontSize: "0.85rem" }}>No saved properties yet.</p>
          <button
            onClick={() => navigate("/")}
            style={{ marginTop: 16, fontSize: "0.82rem", fontWeight: 500, padding: "8px 20px", border: "1px solid var(--rule)", borderRadius: 100, background: "none", cursor: "pointer", color: "var(--ink)" }}
          >
            Start searching
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {favs.map((f: any) => (
            <div
              key={f.id}
              style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: "14px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", background: "var(--white)" }}
              onClick={() => navigate("/properties/" + (f.property_id || f.id))}
            >
              <div>
                <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 2, color: "var(--ink)" }}>{f.property?.title ?? "Saved property"}</p>
                <p style={{ fontSize: "0.75rem", color: "var(--mid)" }}>{f.property?.location ?? ""}{f.property?.price_raw ? " · " + f.property.price_raw : ""}</p>
              </div>
              <ChevronRight size={14} color="var(--mid)" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ViewingsSection() {
  return (
    <div style={{ textAlign: "center", padding: "40px 0", color: "var(--mid)" }}>
      <Calendar size={28} strokeWidth={1} style={{ margin: "0 auto 12px" }} />
      <p style={{ fontSize: "0.85rem" }}>No viewings booked yet.</p>
      <p style={{ fontSize: "0.78rem", marginTop: 6, maxWidth: 280, margin: "8px auto 0" }}>
        When you request viewings through Nave, they'll appear here.
      </p>
    </div>
  );
}

function AlertsSection({ alerts, navigate }: { alerts: any[]; navigate: (s: string) => void }) {
  return (
    <div>
      <p style={{ fontSize: "0.85rem", color: "var(--mid)", marginBottom: 16 }}>
        {alerts?.length ?? 0} active alerts
      </p>
      <button
        onClick={() => navigate("/alerts")}
        style={{ fontSize: "0.82rem", fontWeight: 500, padding: "8px 20px", border: "1px solid var(--rule)", borderRadius: 100, background: "none", cursor: "pointer", color: "var(--ink)", marginBottom: 20 }}
      >
        Manage alerts
      </button>
      {alerts?.map((a: any) => (
        <div key={a.id} style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: "14px 16px", marginBottom: 8, background: "var(--white)" }}>
          <p style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 2, color: "var(--ink)" }}>{a.name}</p>
          <p style={{ fontSize: "0.75rem", color: "var(--mid)" }}>{a.query}</p>
        </div>
      ))}
    </div>
  );
}

function SettingsSection({ logout }: { logout: () => void }) {
  return (
    <div>
      <Card>
        <Row label="Email notifications" value="Enabled"         action="Toggle" />
        <Row label="WhatsApp alerts"      value="Disabled"        action="Toggle" />
        <Row label="Weekly digest"        value="Monday mornings" action="Edit"   />
        <Row label="Alert frequency"      value="Immediate"       action="Edit"   />
      </Card>
      <Card>
        <Row label="Language" value="English (UK)" action="Change" />
        <Row label="Currency" value="GBP £"         action="Change" />
      </Card>
      <Card>
        <Row label="Two-factor authentication" value="Not enabled" action="Enable"    />
        <Row label="Active sessions"           value="1 session"   action="View all" />
        <Row label="Sign out all devices" danger action="Sign out" onClick={logout} />
      </Card>
    </div>
  );
}

function FaqSection() {
  const items = [
    { q: "How does Nave source its listings?",   a: "We aggregate from 30+ sources including Rightmove, Zoopla, church bodies, auction houses, planning portals, and the Charities Commission. Data refreshes every 3 hours." },
    { q: "What does the AI score mean?",              a: "The conversion score (0–10) reflects suitability for your stated purpose — based on listing details, planning status, location, and comparable transactions." },
    { q: "How do pre-market signals work?",           a: "We monitor Charities Commission filings, Companies House dissolutions, and planning applications. These can give 6–18 months advance notice before a property lists." },
    { q: "Is my data safe?",                          a: "Yes. AES-256 encryption, UK data centres, ICO registered. Export or delete your data at any time from your profile." },
    { q: "Can I get WhatsApp alerts?",                a: "Yes — add your phone number in Profile and enable WhatsApp alerts in Settings." },
    { q: "What is a magic link?",                     a: "A one-time secure sign-in link sent to your email. No password required. Expires in 15 minutes, single use only." },
  ];
  return (
    <div>
      <style>{`details summary::-webkit-details-marker { display: none; }`}</style>
      {items.map(({ q, a }) => (
        <details key={q} style={{ borderBottom: "1px solid var(--rule-soft)", paddingBottom: 14, marginBottom: 14 }}>
          <summary style={{ fontSize: "0.88rem", fontWeight: 600, cursor: "pointer", listStyle: "none", display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--ink)" }}>
            {q} <ChevronRight size={14} color="var(--mid)" />
          </summary>
          <p style={{ fontSize: "0.82rem", color: "var(--mid)", lineHeight: 1.65, marginTop: 10 }}>{a}</p>
        </details>
      ))}
    </div>
  );
}

function SupportSection() {
  return (
    <div>
      <p style={{ fontSize: "0.85rem", color: "var(--mid)", marginBottom: 24, lineHeight: 1.65 }}>
        We read every message and aim to respond within 24 hours.
      </p>
      {[
        { label: "Email support",   value: "support@sanctuary.co.uk", action: "Open email" },
        { label: "Report a bug",    value: "Something not working?",  action: "Report"     },
        { label: "Feature request", value: "Suggest something new",   action: "Suggest"    },
      ].map(item => (
        <div key={item.label} style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--white)", marginBottom: 8 }}>
          <div>
            <p style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--ink)" }}>{item.label}</p>
            <p style={{ fontSize: "0.75rem", color: "var(--mid)", marginTop: 2 }}>{item.value}</p>
          </div>
          <span style={{ fontSize: "0.76rem", color: "var(--mid)", cursor: "pointer" }}>{item.action} →</span>
        </div>
      ))}
    </div>
  );
}

function PrivacySection() {
  return (
    <div style={{ fontSize: "0.84rem", color: "var(--mid)", lineHeight: 1.75 }}>
      <p style={{ marginBottom: 16 }}><strong style={{ color: "var(--ink)" }}>Last updated:</strong> June 2026</p>
      {[
        { h: "What we collect",  b: "Email address, name, search preferences, and saved properties. We collect only what is necessary for the service." },
        { h: "How we use it",    b: "To provide property search, alerts, and AI analysis. We do not sell your data or share it with advertisers." },
        { h: "Lawful basis",     b: "Contract (your account), legitimate interest (improving the service), and consent (optional analytics). You can withdraw consent at any time." },
        { h: "Data retention",   b: "Account data is kept while your account is active. Search history is retained for 90 days. Audit logs are kept for 7 years (legal obligation)." },
        { h: "Your rights",      b: "Access, rectification, erasure, portability, and objection under UK GDPR. Contact privacy@sanctuary.co.uk." },
        { h: "Third parties",    b: "We use Supabase (database, UK region), Sentry (error monitoring), and Anthropic (AI analysis). Each is GDPR-compliant." },
      ].map(({ h, b }) => (
        <div key={h} style={{ marginBottom: 18 }}>
          <p style={{ fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>{h}</p>
          <p>{b}</p>
        </div>
      ))}
    </div>
  );
}

function TermsSection() {
  return (
    <div style={{ fontSize: "0.84rem", color: "var(--mid)", lineHeight: 1.75 }}>
      <p style={{ marginBottom: 16 }}><strong style={{ color: "var(--ink)" }}>Last updated:</strong> June 2026</p>
      {[
        { h: "Service description",    b: "Nave aggregates publicly available property listings and provides AI-powered analysis. We are not an estate agent and do not act on your behalf in any transaction." },
        { h: "AI analysis disclaimer", b: "AI scores are indicative only. They do not constitute professional property, legal, or financial advice. Always instruct qualified professionals before purchasing." },
        { h: "Data accuracy",          b: "Listing data is sourced from third parties. We cannot guarantee accuracy or availability. Always verify directly with the source." },
        { h: "Acceptable use",         b: "You may not scrape, automate, or resell data from Nave. The service is for personal property search only." },
        { h: "Governing law",          b: "These terms are governed by English law. Disputes are subject to the exclusive jurisdiction of English courts." },
      ].map(({ h, b }) => (
        <div key={h} style={{ marginBottom: 18 }}>
          <p style={{ fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>{h}</p>
          <p>{b}</p>
        </div>
      ))}
    </div>
  );
}

function LandlordSection() {
  return (
    <div style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: 32, textAlign: "center", background: "var(--white)" }}>
      <Building2 size={32} strokeWidth={1} color="var(--mid)" style={{ margin: "0 auto 16px" }} />
      <p style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: 8, color: "var(--ink)" }}>Coming soon</p>
      <p style={{ fontSize: "0.82rem", color: "var(--mid)", lineHeight: 1.65, maxWidth: 320, margin: "0 auto 20px" }}>
        List your church or gathering space directly on Nave. Reach verified buyers and track interest in real time.
      </p>
      <button style={{ fontSize: "0.82rem", fontWeight: 500, padding: "8px 20px", border: "1px solid var(--rule)", borderRadius: 100, background: "none", cursor: "pointer", color: "var(--ink)" }}>
        Join the waitlist
      </button>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   MAIN PAGE
══════════════════════════════════════════════════════════════════════════ */
export default function AccountPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState<string | null>(null);

  const { data: user }   = useQuery({ queryKey: ["me"],          queryFn: authApi.me,          retry: false });
  const { data: favs }   = useQuery({ queryKey: ["favourites"],  queryFn: favouritesApi.list });
  const { data: alerts } = useQuery({ queryKey: ["alerts"],      queryFn: alertsApi.list });

  function logout() {
    localStorage.removeItem("sanctuary_token");
    navigate("/auth");
  }

  /* ── Sub-page content ─────────────────────────────────────────────────── */
  function renderActive() {
    switch (active) {
      case "profile":  return <ProfileSection  user={user} logout={logout} />;
      case "saved":    return <SavedSection    favs={favs || []} navigate={navigate} />;
      case "viewings": return <ViewingsSection />;
      case "alerts":   return <AlertsSection   alerts={alerts || []} navigate={navigate} />;
      case "settings": return <SettingsSection logout={logout} />;
      case "faq":      return <FaqSection />;
      case "support":  return <SupportSection />;
      case "privacy":  return <PrivacySection />;
      case "terms":    return <TermsSection />;
      case "landlord": return <LandlordSection />;
      default:         return null;
    }
  }

  const activeNav = NAV.find(n => n.id === active);

  return (
    <div style={{ fontFamily: "var(--font-body)", minHeight: "calc(100svh - 52px)" }}>

      {/* ── Desktop: two-column layout ──────────────────────────────────── */}
      <style>{`
        @media (min-width: 768px) {
          .account-mobile-menu  { display: none !important; }
          .account-mobile-sub   { display: none !important; }
          .account-desktop      { display: grid !important; }
        }
        @media (max-width: 767px) {
          .account-desktop      { display: none !important; }
        }
      `}</style>

      {/* Desktop layout */}
      <div
        className="account-desktop wrap"
        style={{ display: "none", gridTemplateColumns: "220px 1fr", gap: 40, paddingTop: 40, paddingBottom: 80 }}
      >
        {/* Sidebar */}
        <div style={{ position: "sticky", top: 72, alignSelf: "start" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24, paddingBottom: 20, borderBottom: "1px solid var(--rule-soft)" }}>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: "var(--ink)", color: "var(--white)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 900, fontSize: "0.9rem", flexShrink: 0 }}>
              {user?.full_name?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontWeight: 600, fontSize: "0.82rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--ink)" }}>{user?.full_name || "Your account"}</p>
              <p style={{ fontSize: "0.72rem", color: "var(--mid)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.email || ""}</p>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {NAV.map(item => {
              const Icon = item.icon;
              const isActive = active === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => !(item as any).soon && setActive(item.id)}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 6, border: "none", background: isActive ? "var(--ink)" : "transparent", color: isActive ? "var(--white)" : (item as any).soon ? "var(--mid)" : "var(--ink)", fontSize: "0.82rem", fontWeight: isActive ? 500 : 400, cursor: (item as any).soon ? "default" : "pointer", textAlign: "left", transition: "all .12s", fontFamily: "var(--font-body)" }}
                >
                  <Icon size={14} style={{ flexShrink: 0 }} />
                  {item.label}
                  {(item as any).soon && (
                    <span style={{ marginLeft: "auto", fontSize: "0.6rem", fontWeight: 500, letterSpacing: ".06em", textTransform: "uppercase", background: "var(--rule-soft)", color: "var(--mid)", padding: "1px 5px", borderRadius: 3 }}>Soon</span>
                  )}
                </button>
              );
            })}
            <button onClick={logout} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 6, border: "none", background: "transparent", color: "var(--red)", fontSize: "0.82rem", cursor: "pointer", textAlign: "left", marginTop: 8, fontFamily: "var(--font-body)" }}>
              <LogOut size={14} style={{ flexShrink: 0 }} /> Log out
            </button>
          </div>
        </div>

        {/* Desktop main content */}
        <div style={{ minWidth: 0 }}>
          {active ? (
            renderActive()
          ) : (
            <div>
              <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", fontWeight: 900, letterSpacing: "-.03em", color: "var(--ink)", marginBottom: 8 }}>
                Your account
              </h2>
              <p style={{ fontSize: "0.85rem", color: "var(--mid)", marginBottom: 24 }}>
                Select a section from the menu.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Mobile: menu list ────────────────────────────────────────────── */}
      <div className="account-mobile-menu" style={{ display: active ? "none" : "block", padding: "28px 20px 60px" }}>

        {/* Avatar row */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28, paddingBottom: 24, borderBottom: "1px solid var(--rule-soft)" }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: "var(--ink)", color: "var(--white)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 900, fontSize: "1.1rem", flexShrink: 0 }}>
            {user?.full_name?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <p style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--ink)" }}>{user?.full_name || "Your account"}</p>
            <p style={{ fontSize: "0.78rem", color: "var(--mid)" }}>{user?.email || ""}</p>
          </div>
        </div>

        {/* Menu items */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          {NAV.map((item, idx) => {
            const Icon = item.icon;
            const soon = (item as any).soon;
            return (
              <button
                key={item.id}
                onClick={() => !soon && setActive(item.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 14,
                  padding: "16px 4px",
                  borderBottom: idx < NAV.length - 1 ? "1px solid var(--rule-soft)" : "none",
                  border: "none", background: "none",
                  cursor: soon ? "default" : "pointer",
                  textAlign: "left", width: "100%",
                  fontFamily: "var(--font-body)",
                  opacity: soon ? 0.5 : 1,
                }}
              >
                <Icon size={18} color="var(--mid)" style={{ flexShrink: 0 }} />
                <span style={{ flex: 1, fontSize: "0.95rem", fontWeight: 500, color: "var(--ink)" }}>
                  {item.label}
                </span>
                {soon
                  ? <span style={{ fontSize: "0.62rem", fontWeight: 500, letterSpacing: ".06em", textTransform: "uppercase", background: "var(--rule-soft)", color: "var(--mid)", padding: "2px 6px", borderRadius: 3 }}>Soon</span>
                  : <ChevronRight size={16} color="var(--mid)" />
                }
              </button>
            );
          })}

          {/* Log out */}
          <button
            onClick={logout}
            style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 4px", border: "none", background: "none", cursor: "pointer", textAlign: "left", width: "100%", fontFamily: "var(--font-body)", marginTop: 8 }}
          >
            <LogOut size={18} color="var(--red)" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: "0.95rem", fontWeight: 500, color: "var(--red)" }}>Log out</span>
          </button>
        </div>
      </div>

      {/* ── Mobile: sub-page ─────────────────────────────────────────────── */}
      <div className="account-mobile-sub" style={{ display: active ? "block" : "none", padding: "28px 20px 60px" }}>
        {active && activeNav && (
          <SubPage title={activeNav.label} onBack={() => setActive(null)}>
            {renderActive()}
          </SubPage>
        )}
      </div>

    </div>
  );
}
