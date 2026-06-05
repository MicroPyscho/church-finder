import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../api/client";

const GOOGLE_ICON = (
  <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
    <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 12.075 17.64 9.767 17.64 9.2z" fill="#4285F4"/>
    <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
    <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
    <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
  </svg>
);

const APPLE_ICON = (
  <svg width="14" height="16" viewBox="0 0 16 18" fill="currentColor">
    <path d="M13.173 9.545c-.02-2.055 1.682-3.048 1.757-3.096-1.26-1.74-3.218-1.979-3.914-2.002-1.663-.168-3.258.977-4.104.977-.854 0-2.152-.957-3.544-.93-1.817.027-3.504 1.053-4.437 2.664C-2.717 10.28.83 15.99 2.56 19.109c.856 1.538 1.869 3.258 3.197 3.203 1.29-.053 1.775-.82 3.334-.82 1.55 0 1.992.82 3.343.793 1.385-.022 2.26-1.556 3.11-3.097.98-1.772 1.385-3.49 1.406-3.579-.03-.014-2.694-1.028-2.717-4.064z"/>
    <path d="M10.012 2.952C10.7 2.115 11.164.97 11.03 0c-.98.04-2.163.65-2.866 1.465-.63.724-1.18 1.882-1.033 2.993 1.095.083 2.21-.553 2.88-1.506z"/>
  </svg>
);

const Eye = ({ open }: { open: boolean }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    {open ? (<><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>) : (<><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></>)}
  </svg>
);

const Shield = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

export default function AuthPage() {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [mode,         setMode]        = useState<"signin"|"signup">("signin");
  const [method,       setMethod]      = useState<"password"|"magic">("password");
  const [email,        setEmail]       = useState("");
  const [password,     setPassword]    = useState("");
  const [name,         setName]        = useState("");
  const [showPass,     setShowPass]    = useState(false);
  const [gdpr,         setGdpr]        = useState(false);
  const [analytics,    setAnalytics]   = useState(false);
  const [magicSent,    setMagicSent]   = useState(false);
  const [error,        setError]       = useState("");
  const [fieldErrors,  setFieldErrors] = useState<Record<string,string>>({});
  const [mounted,      setMounted]     = useState(false);

  /* ── Particle canvas background ───────────────────────────────────────── */
  useEffect(() => {
    setMounted(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);

    const nodes = Array.from({ length: 24 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
      r: Math.random() * 1.2 + 0.4,
    }));

    let id: number;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
        for (let j = i + 1; j < nodes.length; j++) {
          const m = nodes[j];
          const d = Math.hypot(n.x - m.x, n.y - m.y);
          if (d < 130) {
            ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(m.x, m.y);
            ctx.strokeStyle = `rgba(26,26,26,${0.06 * (1 - d / 130)})`;
            ctx.lineWidth = 0.5; ctx.stroke();
          }
        }
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(26,26,26,0.2)"; ctx.fill();
      }
      id = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(id); window.removeEventListener("resize", resize); };
  }, []);

  /* ── Validation ────────────────────────────────────────────────────────── */
  function validate() {
    const errs: Record<string,string> = {};
    if (!email) errs.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = "Enter a valid email";
    if (method === "password") {
      if (!password) errs.password = "Password is required";
      else if (mode === "signup" && password.length < 12) errs.password = "Minimum 12 characters";
    }
    if (mode === "signup" && !name) errs.name = "Name is required";
    if (mode === "signup" && !gdpr) errs.gdpr = "You must accept to continue";
    return errs;
  }

  /* ── Auth mutations ────────────────────────────────────────────────────── */
  const loginMut = useMutation({
    mutationFn: () => authApi.login({ email, password }),
    onSuccess: (d) => { localStorage.setItem("sanctuary_token", d.access_token); navigate("/"); },
    onError: (e: any) => {
      // Same error message for valid/invalid email — prevents enumeration
      setError("Incorrect email or password.");
    },
  });

  const registerMut = useMutation({
    mutationFn: () => authApi.register({ email, password, full_name: name, gdpr_consent: gdpr }),
    onSuccess: () => navigate("/confirmed"),
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Registration failed."),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFieldErrors({});
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }

    if (method === "magic") { setMagicSent(true); return; }
    if (mode === "signin") loginMut.mutate();
    else registerMut.mutate();
  }

  const loading = loginMut.isPending || registerMut.isPending;

  /* ── Styles (inline to keep self-contained) ─────────────────────────────── */
  const S = {
    page: {
      minHeight: "100vh", display: "flex",
      fontFamily: "'Space Grotesk', system-ui, sans-serif",
      background: "#ffffff", position: "relative" as const, overflow: "hidden",
    },
    canvas: { position: "absolute" as const, inset: 0, width: "100%", height: "100%", zIndex: 0 },
    left: {
      flex: 1, display: "flex", flexDirection: "column" as const,
      justifyContent: "space-between", padding: "48px",
      borderRight: "1px solid #e0e0e0", position: "relative" as const, zIndex: 1,
      background: "rgba(255,255,255,0.7)", backdropFilter: "blur(8px)",
    },
    right: {
      width: 460, display: "flex", flexDirection: "column" as const,
      justifyContent: "center", padding: "48px",
      position: "relative" as const, zIndex: 1,
      background: "rgba(255,255,255,0.92)", backdropFilter: "blur(12px)",
    },
    logoMark: {
      fontFamily: "'Gabarito', system-ui, sans-serif",
      fontSize: "1.4rem", fontWeight: 900,
      color: "#1a1a1a", letterSpacing: "-.02em",
      display: "flex", alignItems: "center", gap: 8,
    },
    heroText: {
      fontFamily: "'Gabarito', system-ui, sans-serif",
      fontSize: "clamp(2rem, 3.5vw, 3rem)",
      fontWeight: 900, lineHeight: 1.08,
      color: "#1a1a1a", letterSpacing: "-.04em",
    },
    heroSub: {
      fontSize: "0.9rem", color: "#6b6b6b",
      lineHeight: 1.65, fontWeight: 300, maxWidth: 360,
    },
    pillRow: { display: "flex", flexWrap: "wrap" as const, gap: 6, marginTop: 20 },
    pill: {
      fontSize: "0.7rem", padding: "3px 10px",
      border: "1px solid #e0e0e0", borderRadius: 100,
      color: "#6b6b6b", whiteSpace: "nowrap" as const,
    },
    legal: { fontSize: "0.7rem", color: "#aaaaaa", lineHeight: 1.5 },
    formTitle: {
      fontFamily: "'Gabarito', system-ui, sans-serif",
      fontSize: "1.5rem", fontWeight: 900,
      color: "#1a1a1a", letterSpacing: "-.03em",
      marginBottom: 4,
    },
    formSub: { fontSize: "0.82rem", color: "#6b6b6b", marginBottom: 28 },
    tabs: {
      display: "flex", borderBottom: "1px solid #e0e0e0",
      marginBottom: 24, gap: 0,
    },
    tab: (active: boolean) => ({
      flex: 1, padding: "10px 0", textAlign: "center" as const,
      fontSize: "0.78rem", fontWeight: 500,
      color: active ? "#1a1a1a" : "#6b6b6b",
      borderBottom: active ? "2px solid #1a1a1a" : "2px solid transparent",
      cursor: "pointer", transition: "all .15s",
      background: "none", border: "none",
      borderBottom: active ? "2px solid #1a1a1a" : "2px solid transparent",
    } as React.CSSProperties),
    label: {
      display: "block", fontSize: "0.72rem",
      fontWeight: 500, letterSpacing: ".04em",
      color: "#1a1a1a", marginBottom: 5,
    },
    input: (hasErr: boolean) => ({
      width: "100%", padding: "9px 12px",
      border: `1px solid ${hasErr ? "#d4170f" : "#e0e0e0"}`,
      borderRadius: 6, fontSize: "0.85rem",
      fontFamily: "'Space Grotesk', system-ui, sans-serif",
      color: "#1a1a1a", background: "#ffffff",
      outline: "none", transition: "border-color .15s",
    } as React.CSSProperties),
    fieldErr: { fontSize: "0.72rem", color: "#d4170f", marginTop: 4 },
    magicBox: {
      background: "#f7f7f7", border: "1px solid #e0e0e0",
      borderLeft: "3px solid #3730a3",
      borderRadius: 6, padding: "12px 14px", marginBottom: 20,
      fontSize: "0.8rem", color: "#6b6b6b", lineHeight: 1.6,
    },
    submitBtn: (loading: boolean) => ({
      width: "100%", background: "#1a1a1a",
      border: "none", borderRadius: 100,
      padding: "11px", fontSize: "0.82rem",
      fontWeight: 500, letterSpacing: ".04em",
      color: "#ffffff", cursor: loading ? "not-allowed" : "pointer",
      opacity: loading ? 0.6 : 1,
      transition: "all .15s", marginBottom: 0,
    } as React.CSSProperties),
    divider: {
      display: "flex", alignItems: "center",
      gap: 12, margin: "20px 0",
    },
    divLine: { flex: 1, height: 1, background: "#e0e0e0" },
    divText: {
      fontSize: "0.68rem", fontWeight: 500,
      color: "#aaaaaa", letterSpacing: ".08em",
      textTransform: "uppercase" as const,
    },
    oauthBtn: {
      flex: 1, background: "#ffffff",
      border: "1px solid #e0e0e0", borderRadius: 100,
      padding: "9px", display: "flex",
      alignItems: "center", justifyContent: "center",
      gap: 7, cursor: "pointer",
      fontSize: "0.78rem", fontWeight: 500, color: "#1a1a1a",
      transition: "all .15s",
    } as React.CSSProperties,
    checkRow: {
      display: "flex", alignItems: "flex-start",
      gap: 10, marginBottom: 12,
    },
    checkLabel: { fontSize: "0.76rem", color: "#6b6b6b", lineHeight: 1.5, cursor: "pointer" },
    secNote: {
      display: "flex", alignItems: "center",
      gap: 7, justifyContent: "center",
      paddingTop: 16, marginTop: 16,
      borderTop: "1px solid #f0f0f0",
      fontSize: "0.68rem", color: "#aaaaaa",
    },
    errBox: {
      background: "rgba(212,23,15,.04)",
      border: "1px solid rgba(212,23,15,.3)",
      borderLeft: "3px solid #d4170f",
      borderRadius: 6, padding: "10px 14px",
      fontSize: "0.8rem", color: "#d4170f",
      marginBottom: 16,
    },
  };

  const SOURCE_STATS = ["30+ sources", "Real-time alerts", "AI analysis", "GDPR compliant", "UK hosted"];

  return (
    <div style={S.page}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Gabarito:wght@700;900&family=Space+Grotesk:wght@300;400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        input:-webkit-autofill { -webkit-box-shadow: 0 0 0 40px #fff inset !important; -webkit-text-fill-color: #1a1a1a !important; }
        .auth-input:focus { border-color: #1a1a1a !important; box-shadow: 0 0 0 3px rgba(26,26,26,.06) !important; }
        .oauth-btn:hover { border-color: #1a1a1a !important; background: #f7f7f7 !important; }
        .submit-btn:hover:not(:disabled) { background: #2e2e2e !important; transform: translateY(-1px); }
        .submit-btn:active:not(:disabled) { transform: none; }
        .tab-btn:hover { color: #1a1a1a !important; }
        @keyframes rise { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:none; } }
        .rise { animation: rise .5s cubic-bezier(.16,1,.3,1) both; }
        .rise-1 { animation-delay: .08s; }
        .rise-2 { animation-delay: .14s; }
        .rise-3 { animation-delay: .20s; }
        @media (max-width: 768px) {
          .auth-left { display: none !important; }
          .auth-right { width: 100% !important; }
        }
      `}</style>

      {/* Canvas background */}
      <canvas ref={canvasRef} style={S.canvas} />

      {/* ── Left panel ─────────────────────────────────────────────────── */}
      <div className="auth-left" style={S.left}>
        <div style={S.logoMark}>
          <span style={{ width:8, height:8, borderRadius:"50%", background:"#1a7a3c", flexShrink:0, display:"inline-block" }} />
          Sanctuary
        </div>

        <div>
          <h1 style={S.heroText}>
            Find your next<br />
            <span style={{ position:"relative", display:"inline-block" }}>
              sacred space
              <span style={{
                position:"absolute", bottom:2, left:0, right:0,
                height:3, background:"#7c3aed", borderRadius:2,
              }} />
            </span>
          </h1>
          <p style={{ ...S.heroSub, marginTop: 16 }}>
            30+ sources. AI-powered analysis. Real-time alerts.
            The most complete UK church and gathering space search.
          </p>
          <div style={S.pillRow}>
            {SOURCE_STATS.map(s => <span key={s} style={S.pill}>{s}</span>)}
          </div>
        </div>

        <p style={S.legal}>
          © 2026 Sanctuary. Church &amp; Gathering Space Intelligence.<br />
          UK hosted · ICO registered · GDPR compliant
        </p>
      </div>

      {/* ── Right panel (form) ──────────────────────────────────────────── */}
      <div className="auth-right" style={S.right}>

        {magicSent ? (
          /* ── Magic link sent state ───────────────────────────────────── */
          <div style={{ textAlign:"center", animation:"rise .5s ease both" }}>
            <div style={{
              width:48, height:48, borderRadius:"50%",
              background:"#1a1a1a", color:"#fff",
              display:"flex", alignItems:"center", justifyContent:"center",
              margin:"0 auto 20px", fontSize:"1.2rem",
            }}>✓</div>
            <h2 style={{ ...S.formTitle, marginBottom:8 }}>Check your inbox</h2>
            <p style={{ ...S.formSub, marginBottom:28 }}>
              A secure sign-in link has been sent to <strong>{email}</strong>.<br />
              It expires in 15 minutes and can only be used once.
            </p>
            <button
              style={{ ...S.submitBtn(false), width:"auto", padding:"9px 24px" }}
              className="submit-btn"
              onClick={() => { setMagicSent(false); setEmail(""); }}
            >
              Use a different email
            </button>
            <div style={S.secNote}>
              <Shield /> 256-bit encrypted · GDPR compliant · UK hosted
            </div>
          </div>
        ) : (
          <>
            <div className="rise">
              <h2 style={S.formTitle}>{mode === "signup" ? "Create account" : "Welcome back"}</h2>
              <p style={S.formSub}>{mode === "signup" ? "Start finding your sacred space." : "Sign in to your Sanctuary account."}</p>
            </div>

            {/* ── Method tabs ────────────────────────────────────────────── */}
            <div style={S.tabs}>
              {(["password", "magic"] as const).map(m => (
                <button
                  key={m}
                  style={S.tab(method === m)}
                  className="tab-btn"
                  onClick={() => { setMethod(m); setError(""); setFieldErrors({}); }}
                >
                  {m === "password" ? "Password" : "Magic link"}
                </button>
              ))}
            </div>

            {/* ── Error banner ───────────────────────────────────────────── */}
            {error && <div style={S.errBox}>{error}</div>}

            {/* ── Form ───────────────────────────────────────────────────── */}
            <form onSubmit={handleSubmit} noValidate>

              {/* Name (signup only) */}
              {mode === "signup" && (
                <div className="rise rise-1" style={{ marginBottom:14 }}>
                  <label style={S.label}>Full name</label>
                  <input
                    className="auth-input"
                    style={S.input(!!fieldErrors.name)}
                    value={name} onChange={e => setName(e.target.value)}
                    placeholder="Your name" autoComplete="name"
                  />
                  {fieldErrors.name && <p style={S.fieldErr}>{fieldErrors.name}</p>}
                </div>
              )}

              {/* Email */}
              <div className="rise rise-1" style={{ marginBottom:14 }}>
                <label style={S.label}>Email address</label>
                <input
                  className="auth-input"
                  type="email" style={S.input(!!fieldErrors.email)}
                  value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com" autoComplete="email"
                />
                {fieldErrors.email && <p style={S.fieldErr}>{fieldErrors.email}</p>}
              </div>

              {/* Password */}
              {method === "password" && (
                <div className="rise rise-2" style={{ marginBottom:20 }}>
                  <label style={S.label}>Password</label>
                  <div style={{ position:"relative" }}>
                    <input
                      className="auth-input"
                      type={showPass ? "text" : "password"}
                      style={{ ...S.input(!!fieldErrors.password), paddingRight:40 }}
                      value={password} onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      autoComplete={mode === "signup" ? "new-password" : "current-password"}
                    />
                    <button
                      type="button" onClick={() => setShowPass(v => !v)}
                      style={{ position:"absolute", right:12, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", color:"#aaaaaa", cursor:"pointer", padding:2, lineHeight:0 }}
                    >
                      <Eye open={showPass} />
                    </button>
                  </div>
                  {fieldErrors.password && <p style={S.fieldErr}>{fieldErrors.password}</p>}
                  {mode === "signin" && (
                    <div style={{ textAlign:"right", marginTop:6 }}>
                      <span style={{ fontSize:"0.72rem", color:"#aaaaaa", cursor:"pointer", textDecoration:"underline" }}>Forgot password?</span>
                    </div>
                  )}
                  {mode === "signup" && (
                    <p style={{ fontSize:"0.68rem", color:"#aaaaaa", marginTop:5 }}>Minimum 12 characters</p>
                  )}
                </div>
              )}

              {/* Magic link info */}
              {method === "magic" && (
                <div style={S.magicBox} className="rise rise-2">
                  We'll send a one-time secure link to your email. No password. Expires in 15 minutes.
                </div>
              )}

              {/* GDPR consent (signup only) */}
              {mode === "signup" && (
                <div className="rise rise-3">
                  <label style={S.checkRow}>
                    <input
                      type="checkbox" checked={gdpr} onChange={e => setGdpr(e.target.checked)}
                      style={{ marginTop:2, accentColor:"#1a1a1a", flexShrink:0 }}
                    />
                    <span style={S.checkLabel}>
                      I agree to the <span style={{ textDecoration:"underline", cursor:"pointer" }}>Terms of Service</span> and <span style={{ textDecoration:"underline", cursor:"pointer" }}>Privacy Policy</span>. I understand my data is processed under GDPR and I can request deletion at any time.
                    </span>
                  </label>
                  {fieldErrors.gdpr && <p style={{ ...S.fieldErr, marginBottom:8 }}>{fieldErrors.gdpr}</p>}

                  <label style={S.checkRow}>
                    <input
                      type="checkbox" checked={analytics} onChange={e => setAnalytics(e.target.checked)}
                      style={{ marginTop:2, accentColor:"#1a1a1a", flexShrink:0 }}
                    />
                    <span style={S.checkLabel}>
                      I consent to anonymised usage analytics to improve the service (optional — withdrawable at any time).
                    </span>
                  </label>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                className="submit-btn"
                style={{ ...S.submitBtn(loading), marginTop:20 }}
                disabled={loading}
              >
                {loading ? "Please wait…" : method === "magic" ? "Send secure link" : mode === "signup" ? "Create account" : "Sign in"}
              </button>
            </form>

            {/* Divider */}
            <div style={S.divider}>
              <div style={S.divLine} />
              <span style={S.divText}>or continue with</span>
              <div style={S.divLine} />
            </div>

            {/* OAuth */}
            <div style={{ display:"flex", gap:10, marginBottom:24 }}>
              {[{icon:GOOGLE_ICON,label:"Google"},{icon:APPLE_ICON,label:"Apple"}].map(({icon,label}) => (
                <button key={label} className="oauth-btn" style={S.oauthBtn}>
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Toggle mode */}
            <p style={{ textAlign:"center", fontSize:"0.8rem", color:"#6b6b6b" }}>
              {mode === "signup" ? "Already have an account? " : "New here? "}
              <span
                onClick={() => { setMode(m => m === "signup" ? "signin" : "signup"); setError(""); setFieldErrors({}); }}
                style={{ color:"#1a1a1a", textDecoration:"underline", cursor:"pointer", fontWeight:500 }}
              >
                {mode === "signup" ? "Sign in" : "Create account"}
              </span>
            </p>

            {/* Security note */}
            <div style={S.secNote}>
              <Shield /> 256-bit encrypted · GDPR Art. 6 · UK hosted · ICO registered
            </div>
          </>
        )}
      </div>
    </div>
  );
}
