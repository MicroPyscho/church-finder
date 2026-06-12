import { useState } from "react";
import { X, Heart, Mail, Church, Eye, EyeOff } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { api } from "../../api/client";

export default function AuthGateModal() {
  const { showAuthGate, gateReason, closeGate, setUser } = useAuthStore();
  const [mode,      setMode]      = useState<"signin" | "signup">("signup");
  const [email,     setEmail]     = useState("");
  const [password,  setPassword]  = useState("");
  const [name,      setName]      = useState("");
  const [showPw,    setShowPw]    = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");

  if (!showAuthGate) return null;

  const REASON_TEXT = {
    favourite: {
      icon:  <Heart size={20} color="#d4170f" fill="#d4170f"/>,
      title: "Save this property",
      sub:   "Create a free account to save properties and pick up where you left off.",
    },
    enquiry: {
      icon:  <Mail size={20} color="var(--ink)"/>,
      title: "Contact the agent",
      sub:   "Create a free account to send enquiries and track your conversations.",
    },
  };
  const ctx = REASON_TEXT[gateReason || "favourite"];

  async function handleSubmit() {
    setError("");
    if (!email || !password) { setError("Please fill in all fields"); return; }
    if (mode === "signup" && !name) { setError("Please enter your name"); return; }
    setLoading(true);
    try {
      if (mode === "signup") {
        const r = await api.post("/api/auth/register", { email, name, password });
        const { access_token, user } = r.data;
        localStorage.setItem("sanctuary_token", access_token);
        setUser(user);
      } else {
        const params = new URLSearchParams();
        params.append("username", email);
        params.append("password", password);
        const r = await api.post("/api/auth/login", params, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" }
        });
        const { access_token, user } = r.data;
        localStorage.setItem("sanctuary_token", access_token);
        setUser(user);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && closeGate()}>
      <div className="modal" style={{ maxWidth:420, position:"relative" }}>

        {/* Close */}
        <button onClick={closeGate} style={{
          position:"absolute", top:16, right:16,
          background:"none", border:"none", cursor:"pointer", color:"var(--mid)",
        }}>
          <X size={18}/>
        </button>

        {/* Reason */}
        <div style={{ textAlign:"center", marginBottom:24 }}>
          <div style={{ marginBottom:12 }}>{ctx.icon}</div>
          <h2 style={{ fontSize:"1.1rem", fontWeight:700, marginBottom:6 }}>{ctx.title}</h2>
          <p style={{ fontSize:"0.82rem", color:"var(--mid)", lineHeight:1.5 }}>{ctx.sub}</p>
        </div>

        {/* Toggle */}
        <div style={{
          display:"flex", marginBottom:20,
          border:"1px solid var(--rule)", borderRadius:"var(--r)", overflow:"hidden",
        }}>
          {(["signup","signin"] as const).map(m => (
            <button key={m} onClick={() => { setMode(m); setError(""); }} style={{
              flex:1, padding:"8px 0", fontSize:"0.78rem", fontWeight:600,
              border:"none", cursor:"pointer",
              background: mode === m ? "var(--ink)" : "transparent",
              color:      mode === m ? "#fff" : "var(--mid)",
            }}>
              {m === "signup" ? "Create account" : "Sign in"}
            </button>
          ))}
        </div>

        {/* Form */}
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {mode === "signup" && (
            <input className="form-input" placeholder="Your full name"
              value={name} onChange={e => setName(e.target.value)} autoFocus />
          )}

          <input className="form-input" type="email" placeholder="Email address"
            value={email} onChange={e => setEmail(e.target.value)} />

          {/* Password with eye toggle */}
          <div style={{ position:"relative" }}>
            <input className="form-input"
              type={showPw ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
              style={{ paddingRight:40, width:"100%", boxSizing:"border-box" }}
            />
            <button
              type="button"
              onClick={() => setShowPw(p => !p)}
              style={{
                position:"absolute", right:10, top:"50%", transform:"translateY(-50%)",
                background:"none", border:"none", cursor:"pointer",
                color:"var(--mid)", padding:0, lineHeight:0,
              }}
              title={showPw ? "Hide password" : "Show password"}
            >
              {showPw ? <EyeOff size={15}/> : <Eye size={15}/>}
            </button>
          </div>

          {error && (
            <p style={{ color:"#e53e3e", fontSize:"0.75rem", margin:0 }}>{error}</p>
          )}

          <button className="btn btn-black" style={{ marginTop:4 }}
            onClick={handleSubmit} disabled={loading}>
            {loading ? "…" : mode === "signup" ? "Create free account" : "Sign in"}
          </button>
        </div>

        {/* Free reminder */}
        <div style={{
          marginTop:20, paddingTop:16,
          borderTop:"1px solid var(--rule)", textAlign:"center",
        }}>
          <p style={{ fontSize:"0.72rem", color:"var(--mid)", margin:0 }}>
            <Church size={11} style={{ verticalAlign:"middle", marginRight:4 }}/>
            Searching and browsing is always free — no account needed
          </p>
        </div>
      </div>
    </div>
  );
}
