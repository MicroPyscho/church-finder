import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { X, Mail, Edit3 } from "lucide-react";
import { api } from "../../api/client";

interface Props {
  property:  any;
  onClose:   () => void;
  onSent:    () => void;
  intent?:   any;
}

export default function InterestModal({ property: p, onClose, onSent, intent }: Props) {
  const [name,  setName]  = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [draft, setDraft] = useState<{ subject: string; body: string } | null>(null);
  const [step,  setStep]  = useState<"form" | "preview">("form");
  const [copied, setCopied] = useState(false);

  // Call our Groq-powered enquiry endpoint
  const draftMut = useMutation({
    mutationFn: () =>
      api.post("/api/enquiry/draft", {
        property_id:      p.id,
        property_data:    p,
        user_intent:      intent || null,
        user_description: notes || null,
      }).then(r => r.data),
    onSuccess: (d) => {
      setDraft(d);
      setStep("preview");
    },
  });

  // Send — currently opens mailto, SMTP sending when configured
  const sendMut = useMutation({
    mutationFn: () =>
      api.post("/api/enquiry/send", {
        property_id:   p.id,
        property_data: p,
        user_intent:   intent || null,
      }).then(r => r.data),
    onSuccess: onSent,
  });

  function openMailto() {
    if (!draft) return;
    const subject = encodeURIComponent(draft.subject);
    const body    = encodeURIComponent(
      `${draft.body}\n\n---\nSent by: ${name}\nEmail: ${email}${phone ? `\nPhone: ${phone}` : ""}`
    );
    const to = p.source_url?.includes("alex-martin") ? "info@alex-martin.co.uk" :
               p.source_url?.includes("sw.co.uk")    ? "info@sw.co.uk"          : "";
    window.open(`mailto:${to}?subject=${subject}&body=${body}`, "_blank");
    onSent();
  }

  function copyToClipboard() {
    if (!draft) return;
    navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">

        {/* Header */}
        <div style={{ display:"flex", justifyContent:"space-between",
                      alignItems:"flex-start", marginBottom:20 }}>
          <div>
            <h2 className="modal-title">Express interest</h2>
            <p className="modal-sub" style={{ marginBottom:0 }}>{p.title}</p>
          </div>
          <button onClick={onClose}
            style={{ color:"var(--mid)", padding:4, lineHeight:0, background:"none", border:"none", cursor:"pointer" }}>
            <X size={18}/>
          </button>
        </div>

        {step === "form" ? (
          <>
            {[
              { l:"Your name",         v:name,  s:setName,  pl:"Full name",       t:"text"  },
              { l:"Email",             v:email, s:setEmail, pl:"your@email.com",  t:"email" },
              { l:"Phone (optional)",  v:phone, s:setPhone, pl:"+44 7700…",       t:"tel"   },
            ].map(f => (
              <div key={f.l} className="form-row">
                <label className="form-label">{f.l}</label>
                <input className="form-input" type={f.t} value={f.v}
                  onChange={e => f.s(e.target.value)} placeholder={f.pl} />
              </div>
            ))}

            <div className="form-row">
              <label className="form-label">
                Notes for AI (optional)
                <span style={{ color:"var(--mid)", fontWeight:400, marginLeft:6 }}>
                  — what to ask, your intended use, budget
                </span>
              </label>
              <textarea className="form-textarea" value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="e.g. I plan to convert to community use, budget £200k, interested in listed status…"
                rows={3}
              />
            </div>

            {draftMut.isError && (
              <p style={{ color:"#e53e3e", fontSize:"0.78rem", marginBottom:12 }}>
                Could not generate draft. Please try again.
              </p>
            )}

            <div className="modal-actions">
              <button className="btn-modal ghost" onClick={onClose}>Cancel</button>
              <button className="btn-modal solid"
                onClick={() => draftMut.mutate()}
                disabled={!name || !email || draftMut.isPending}>
                {draftMut.isPending
                  ? "Drafting…"
                  : <><Edit3 size={13}/> Draft with AI →</>
                }
              </button>
            </div>
          </>
        ) : (
          <>
            {/* AI draft preview */}
            <div style={{
              background:"var(--off-white)", border:"1px solid var(--rule)",
              borderRadius:"var(--r)", padding:16, marginBottom:20,
            }}>
              <p style={{ fontSize:"0.72rem", letterSpacing:".08em",
                          textTransform:"uppercase", color:"var(--mid)", marginBottom:8 }}>
                AI-drafted enquiry
              </p>
              <p style={{ fontSize:"0.82rem", fontWeight:600, marginBottom:8 }}>
                {draft?.subject}
              </p>
              <p style={{ fontSize:"0.8rem", color:"var(--ink-soft)",
                          lineHeight:1.65, whiteSpace:"pre-wrap" }}>
                {draft?.body}
              </p>
            </div>

            <div className="modal-actions" style={{ flexWrap:"wrap", gap:8 }}>
              <button className="btn-modal ghost" onClick={() => setStep("form")}>
                ← Edit
              </button>
              <button className="btn-modal ghost" onClick={copyToClipboard}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
              <button className="btn-modal solid" onClick={openMailto}>
                <Mail size={13}/> Open in Mail
              </button>
            </div>

            <p style={{ fontSize:"0.68rem", color:"var(--mid)", marginTop:12, textAlign:"center" }}>
              This will open your email client with the draft ready to send.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
