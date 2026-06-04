import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "../api/client";

export default function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode]   = useState<"login"|"register">("login");
  const [email,setEmail]  = useState("");
  const [pass, setPass]   = useState("");
  const [name, setName]   = useState("");
  const [gdpr, setGdpr]   = useState(false);
  const [err,  setErr]    = useState("");

  const loginMut = useMutation({
    mutationFn: ()=>authApi.login({email,password:pass}),
    onSuccess: (d)=>{ localStorage.setItem("sanctuary_token",d.access_token); navigate(-1); },
    onError: ()=>setErr("Invalid email or password."),
  });

  const regMut = useMutation({
    mutationFn: ()=>authApi.register({email,password:pass,full_name:name,gdpr_consent:gdpr}),
    onSuccess: ()=>navigate("/confirmed"),
    onError: (e:any)=>setErr(e?.response?.data?.detail??"Registration failed."),
  });

  return (
    <div className="auth-page">
      <div className="auth-box">
        <h1 className="auth-title">{mode==="login"?"Welcome back":"Create account"}</h1>
        <p className="auth-sub">{mode==="login"?"Sign in to access your saved properties and alerts.":"Save searches, get alerts, and contact sellers."}</p>

        {err&&(
          <div style={{padding:"10px 14px",border:"1px solid rgba(212,23,15,.3)",borderLeft:"3px solid var(--red)",borderRadius:"var(--r)",fontSize:"0.82rem",color:"var(--red)",marginBottom:16}}>{err}</div>
        )}

        {mode==="register"&&(
          <div className="form-row">
            <label className="form-label">Full name</label>
            <input className="form-input" value={name} onChange={e=>setName(e.target.value)} placeholder="Your name"/>
          </div>
        )}
        <div className="form-row">
          <label className="form-label">Email</label>
          <input className="form-input" type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/>
        </div>
        <div className="form-row">
          <label className="form-label">Password</label>
          <input className="form-input" type="password" value={pass} onChange={e=>setPass(e.target.value)} placeholder="••••••••" onKeyDown={e=>e.key==="Enter"&&(mode==="login"?loginMut.mutate():regMut.mutate())}/>
        </div>

        {mode==="register"&&(
          <label style={{display:"flex",alignItems:"flex-start",gap:10,fontSize:"0.78rem",color:"var(--mid)",marginBottom:16,cursor:"pointer"}}>
            <input type="checkbox" checked={gdpr} onChange={e=>setGdpr(e.target.checked)} style={{marginTop:2,accentColor:"var(--ink)"}}/>
            I agree to my data being used for property search and alerts. I can request deletion at any time.
          </label>
        )}

        <button
          className="btn btn-black"
          style={{width:"100%",justifyContent:"center",marginBottom:12}}
          onClick={()=>mode==="login"?loginMut.mutate():regMut.mutate()}
          disabled={loginMut.isPending||regMut.isPending||(mode==="register"&&!gdpr)}
        >
          {loginMut.isPending||regMut.isPending?"Please wait…":mode==="login"?"Sign in":"Create account"}
        </button>

        <p className="auth-link">
          {mode==="login"
            ?<>No account? <a onClick={()=>{setMode("register");setErr("");}}>Create one</a></>
            :<>Already have one? <a onClick={()=>{setMode("login");setErr("");}}>Sign in</a></>}
        </p>
      </div>
    </div>
  );
}
