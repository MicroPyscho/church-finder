import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { X } from "lucide-react";
import { outreachApi } from "../../api/client";

interface Props { property:any; onClose:()=>void; onSent:()=>void; }

export default function InterestModal({ property:p, onClose, onSent }:Props) {
  const [name,   setName]   = useState("");
  const [email,  setEmail]  = useState("");
  const [phone,  setPhone]  = useState("");
  const [msg,    setMsg]    = useState("");
  const [draft,  setDraft]  = useState<any>(null);
  const [step,   setStep]   = useState<"form"|"preview">("form");

  const draftMut = useMutation({
    mutationFn: () => outreachApi.draft({ property_id:p.id, intent:"interested buyer" }),
    onSuccess: (d) => { setDraft(d); setStep("preview"); },
  });

  const sendMut = useMutation({
    mutationFn: () => outreachApi.send({ property_id:p.id, subject:draft?.subject??`Interest in ${p.title}`, body:draft?.body??msg }),
    onSuccess: onSent,
  });

  return (
    <div className="overlay" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal">
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:20}}>
          <div>
            <h2 className="modal-title">Express interest</h2>
            <p className="modal-sub" style={{marginBottom:0}}>{p.title}</p>
          </div>
          <button onClick={onClose} style={{color:"var(--mid)",padding:4,lineHeight:0}}><X size={18}/></button>
        </div>

        {step==="form" ? (
          <>
            {[
              {l:"Your name",v:name,s:setName,p:"Full name",t:"text"},
              {l:"Email",    v:email,s:setEmail,p:"your@email.com",t:"email"},
              {l:"Phone (optional)",v:phone,s:setPhone,p:"+44 7700…",t:"tel"},
            ].map(f => (
              <div key={f.l} className="form-row">
                <label className="form-label">{f.l}</label>
                <input className="form-input" type={f.t} value={f.v} onChange={e=>f.s(e.target.value)} placeholder={f.p}/>
              </div>
            ))}
            <div className="form-row">
              <label className="form-label">Message (optional — AI will draft if blank)</label>
              <textarea className="form-textarea" value={msg} onChange={e=>setMsg(e.target.value)} placeholder="Any specific questions…"/>
            </div>
            <div className="modal-actions">
              <button className="btn-modal ghost" onClick={onClose}>Cancel</button>
              <button className="btn-modal solid" onClick={()=>draftMut.mutate()} disabled={!name||!email||draftMut.isPending}>
                {draftMut.isPending?"Drafting…":"Preview AI email →"}
              </button>
            </div>
          </>
        ) : (
          <>
            <div style={{background:"var(--off-white)",border:"1px solid var(--rule)",borderRadius:"var(--r)",padding:16,marginBottom:20}}>
              <p style={{fontSize:"0.72rem",letterSpacing:".08em",textTransform:"uppercase",color:"var(--mid)",marginBottom:8}}>AI-drafted email</p>
              <p style={{fontSize:"0.82rem",fontWeight:600,marginBottom:8}}>{draft?.subject}</p>
              <p style={{fontSize:"0.8rem",color:"var(--ink-soft)",lineHeight:1.65,whiteSpace:"pre-wrap"}}>{draft?.body}</p>
            </div>
            <div className="modal-actions">
              <button className="btn-modal ghost" onClick={()=>setStep("form")}>← Edit</button>
              <button className="btn-modal solid" onClick={()=>sendMut.mutate()} disabled={sendMut.isPending}>
                {sendMut.isPending?"Sending…":"Send email"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
