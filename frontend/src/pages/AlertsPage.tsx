import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Trash2, Plus, Check } from "lucide-react";
import { alertsApi } from "../api/client";

export default function AlertsPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState({name:"My Alert",query:"",max_price:"",counties:"",min_ai_score:"0"});
  const [saved,setSaved]= useState(false);

  const { data:alerts } = useQuery({ queryKey:["alerts"], queryFn:alertsApi.list });

  const createMut = useMutation({
    mutationFn: (d:any)=>alertsApi.create(d),
    onSuccess: () => { qc.invalidateQueries({queryKey:["alerts"]}); setSaved(true); setTimeout(()=>setSaved(false),3000); },
  });

  const deleteMut = useMutation({
    mutationFn: alertsApi.delete,
    onSuccess: () => qc.invalidateQueries({queryKey:["alerts"]}),
  });

  return (
    <div className="wrap" style={{paddingTop:40,paddingBottom:80,maxWidth:720}}>
      <h1 style={{fontFamily:"var(--font-display)",fontSize:"2rem",fontWeight:900,letterSpacing:"-.03em",marginBottom:6}}>Alerts</h1>
      <p style={{fontSize:"0.88rem",color:"var(--mid)",marginBottom:36}}>Get notified the moment a matching property appears</p>

      <div style={{border:"1px solid var(--rule)",borderRadius:"var(--r2)",padding:24,marginBottom:32,background:"var(--off-white)"}}>
        <h2 style={{fontFamily:"var(--font-display)",fontSize:"1rem",fontWeight:700,marginBottom:18,display:"flex",alignItems:"center",gap:6}}>
          <Plus size={14}/> New alert
        </h2>
        {[
          {k:"name",        l:"Alert name",               p:"e.g. Churches under £200k, Kent"},
          {k:"query",       l:"Search keywords",          p:"e.g. former methodist chapel"},
          {k:"max_price",   l:"Max price (£)",            p:"e.g. 250000"},
          {k:"counties",    l:"Counties (comma-separated)",p:"e.g. Kent, Surrey, Essex"},
          {k:"min_ai_score",l:"Min AI score (0–10)",      p:"e.g. 6"},
        ].map(f=>(
          <div key={f.k} className="form-row">
            <label className="form-label">{f.l}</label>
            <input className="form-input" placeholder={f.p} value={(form as any)[f.k]} onChange={e=>setForm(x=>({...x,[f.k]:e.target.value}))}/>
          </div>
        ))}
        <button
          className="btn btn-black"
          style={{marginTop:8}}
          onClick={()=>createMut.mutate({...form,max_price:form.max_price?+form.max_price:null,min_ai_score:+form.min_ai_score})}
          disabled={createMut.isPending}
        >
          {saved?<><Check size={13}/> Alert created</>:<><Bell size={13}/> Create alert</>}
        </button>
      </div>

      <h2 style={{fontFamily:"var(--font-display)",fontSize:"0.9rem",fontWeight:700,marginBottom:12}}>
        Active alerts ({alerts?.length??0})
      </h2>

      {!alerts?.length&&(
        <div className="empty"><div className="empty__icon"><Bell size={28} strokeWidth={1}/></div><div className="empty__title">No alerts yet</div></div>
      )}

      {alerts?.map((a:any)=>(
        <div key={a.id} className="alert-card active">
          <div>
            <div className="alert-name">{a.name}</div>
            <div className="alert-meta">
              {a.query&&<span>Keywords: {a.query} · </span>}
              {a.max_price&&<span>Max £{a.max_price.toLocaleString()} · </span>}
              {a.counties&&<span>Counties: {a.counties}</span>}
            </div>
          </div>
          <button className="btn-sm" onClick={()=>deleteMut.mutate(a.id)} style={{flexShrink:0}}>
            <Trash2 size={12}/> Remove
          </button>
        </div>
      ))}
    </div>
  );
}
