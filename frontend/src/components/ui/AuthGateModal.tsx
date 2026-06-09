import { useState } from "react";
import { X, Heart, Mail, Church } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

export default function AuthGateModal() {
  const { showAuthGate, gateReason, closeGate, setUser } = useAuthStore();
  const [mode,     setMode]     = useState<"signin" | "signup">("signup");
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [name,     setName]     = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  if (!showAuthGate) return null;

  const REASON_TEXT = {
    favourite: { icon: <Heart size={20} color="#d4170f"/>, title: "Save this property", sub: "Create a free account to save properties and pick up where you left off." },
    enquiry:   { icon: <Mail size={20} color="var(--ink)"/>, title: "Contact the agent", sub: "Create a free account to send enquiries and track your conversations." },
  };
  const ctx = REASON_TEXT[gateReason || "favourite"];

  async function handleSubmit() {
    if (!email || !password) { setError("Please fill in all fields"); return; }
    if (mode === "signup" && !name) { setError("Please enter your name"); return; }
    setLoading(true);
    setError("");
    // Simulate auth for now — wire to /api/auth when ready
    await new Promise(r => setTimeout(r, 800));
    setUser({ name: name || email.split("@")[0], email });
    setLoading(false);
  }

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && closeGate()}>
      <div className="modal" style={{ maxWidth: 420 }}>

        {/* Close */}
        <button onClick={closeGate} style={{
          position:"absolute", top:16, right:16,
          background:"none", border:"none", cursor:"pointer", color:"var(--mid)"
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
        <div style={{ display:"flex", gap:0, marginBottom:20,
                      border:"1px solid var(--rule)", borderRadius:"var(--r)", overflow:"hidden" }}>
          {(["signup","signin"] as const).map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              flex:1, padding:"8px 0", fontSize:"0.78rem", fontWeight:600,
              border:"none", cursor:"pointer",
              background: mode === m ? "var(--ink)" : "transparent",
              color: mode === m ? "#fff" : "var(--mid)",
            }}>
              {m === "signup" ? "Create account" : "Sign in"}
            </button>
          ))}
        </div>

        {/* Form */}
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {mode === "signup" && (
            <input className="form-input" placeholder="Your name"
              value={name} onChange={e => setName(e.target.value)} />
          )}
          <input className="form-input" type="email" placeholder="Email address"
            value={email} onChange={e => setEmail(e.target.value)} />
          <input className="form-input" type="password" placeholder="Password"
            value={password} onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSubmit()} />

          {error && <p style={{ color:"#e53e3e", fontSize:"0.75rem" }}>{error}</p>}

          <button className="btn btn-black" style={{ marginTop:4 }}
            onClick={handleSubmit} disabled={loading}>
            {loading ? "…" : mode === "signup" ? "Create free account" : "Sign in"}
          </button>
        </div>

        {/* Free features reminder */}
        <div style={{ marginTop:20, padding:"12px 0",
                      borderTop:"1px solid var(--rule)", textAlign:"center" }}>
          <p style={{ fontSize:"0.72rem", color:"var(--mid)" }}>
            <Church size={11} style={{ verticalAlign:"middle", marginRight:4 }}/>
            Searching and browsing is always free — no account needed
          </p>
        </div>
      </div>
    </div>
  );
}
