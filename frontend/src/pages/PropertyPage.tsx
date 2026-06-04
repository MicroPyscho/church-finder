import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Heart, ExternalLink, RefreshCw, AlertTriangle, Mail } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { propertyApi, favouritesApi, outreachApi } from "../api/client";
import InterestModal from "../components/ui/InterestModal";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const FEATS:[string,string,string][]=[
  ["has_parking","🅿️","Parking"],["has_graveyard","⚰️","Graveyard"],
  ["has_balcony","🪟","Balcony"],["has_porch","🚪","Porch"],
  ["has_hall","🏛","Hall"],["has_spire","⛪","Spire"],
  ["has_organ","🎵","Organ"],["has_vestry","📦","Vestry"],
];

export default function PropertyPage() {
  const { id }   = useParams<{id:string}>();
  const navigate = useNavigate();
  const qc       = useQueryClient();
  const [faved,   setFaved]    = useState(false);
  const [modal,   setModal]    = useState(false);
  const [stream,  setStream]   = useState("");
  const [streaming,setStreaming]= useState(false);
  const didStream = useRef(false);

  const { data:prop, isLoading } = useQuery({
    queryKey:["property",id], queryFn:()=>propertyApi.get(id!), enabled:!!id,
  });

  const { data:analysis } = useQuery({
    queryKey:["analysis",id], queryFn:()=>propertyApi.analysis(id!), enabled:!!id, staleTime:Infinity,
  });

  const favMut = useMutation({
    mutationFn:()=>faved?favouritesApi.remove(id!):favouritesApi.add(id!),
    onSuccess:()=>{ setFaved(f=>!f); qc.invalidateQueries({queryKey:["favourites"]}); },
  });

  useEffect(()=>{ if (prop&&!didStream.current){ didStream.current=true; doStream(); } },[prop]);

  async function doStream() {
    setStream(""); setStreaming(true);
    try {
      const res = await fetch(`${BASE}/api/search/stream-analysis/${id}`);
      if (!res.body) return;
      const reader=res.body.getReader(); const dec=new TextDecoder();
      while(true) {
        const {done,value}=await reader.read(); if(done) break;
        for (const line of dec.decode(value).split("\n")) {
          if (line.startsWith("data: ")) {
            const d=line.slice(6); if(d==="[DONE]") break;
            try { const p=JSON.parse(d); if(p.text) setStream(t=>t+p.text); } catch{}
          }
        }
      }
    } finally { setStreaming(false); }
  }

  if (isLoading) return <div className="wrap detail"><div className="skeleton" style={{height:400,borderRadius:"var(--r2)"}}/></div>;
  if (!prop) return <div className="wrap detail" style={{textAlign:"center"}}><p>Property not found. <button className="btn-ghost btn" onClick={()=>navigate(-1)}>Go back</button></p></div>;

  const feats = FEATS.filter(([k])=>(prop as any)[k]);
  const ai    = analysis?.analysis??{};
  const aiUses= (()=>{try{return JSON.parse(prop.ai_uses||"[]");}catch{return [];}})();
  const aiRisks=(()=>{try{return JSON.parse(prop.ai_risks||"[]");}catch{return [];}})();

  return (
    <div className="wrap detail">
      <button className="detail-back" onClick={()=>navigate(-1)}><ArrowLeft size={13}/> Back to results</button>

      <div className="detail-grid">
        <div>
          <p className="detail-source">{prop.source}</p>
          <h1 className="detail-title">{prop.title}</h1>
          <p className="detail-price">{prop.price_raw||"POA"}</p>

          <div className="detail-meta">
            <span>📍 {prop.location}</span>
            {prop.county&&<span>{prop.county}</span>}
            {prop.postcode&&<span>{prop.postcode}</span>}
            <span>{formatDistanceToNow(new Date(prop.first_seen),{addSuffix:true})}</span>
          </div>

          <div className="detail-flags">
            {prop.is_listed&&<span className="tag">Grade {prop.listed_grade} Listed</span>}
            {prop.in_conservation&&<span className="tag">Conservation Area</span>}
            {prop.heritage_at_risk&&<span className="tag heritage">Heritage at Risk</span>}
            {prop.dissolution_notice&&<span className="tag signal">Dissolution Notice</span>}
            {prop.has_mortgage_charge&&<span className="tag signal">Mortgage Charge</span>}
            {prop.listing_type==="auction"&&<span className="tag auction">Auction</span>}
          </div>

          {feats.length>0&&(
            <div className="card-features" style={{marginBottom:20}}>
              {feats.map(([,icon,label])=><span key={label} className="feat">{icon} {label}</span>)}
              {prop.acreage&&<span className="feat">📐 {prop.acreage} acres</span>}
              {prop.floor_area_sqft&&<span className="feat">📏 {prop.floor_area_sqft.toLocaleString()} sqft</span>}
            </div>
          )}

          <div style={{display:"flex",gap:8,marginBottom:28,flexWrap:"wrap"}}>
            <a href={prop.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-black"><ExternalLink size={13}/> View on {prop.source}</a>
            <button className="btn btn-outline" onClick={()=>favMut.mutate()}><Heart size={13} fill={faved?"currentColor":"none"}/> {faved?"Saved":"Save"}</button>
            <button className="btn btn-outline" onClick={()=>setModal(true)}><Mail size={13}/> Express interest</button>
          </div>

          {prop.description&&<p className="detail-desc">{prop.description}</p>}

          {prop.financial_distress_score>4&&(
            <div style={{padding:"14px 16px",border:"1px solid rgba(245,166,35,.4)",borderLeft:"3px solid var(--yellow)",borderRadius:"var(--r2)",marginBottom:24,background:"rgba(245,166,35,.04)"}}>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
                <AlertTriangle size={14} color="var(--yellow)"/>
                <strong style={{fontSize:"0.83rem"}}>Financial distress signals detected</strong>
              </div>
              <p style={{fontSize:"0.78rem",color:"var(--mid)",lineHeight:1.55}}>
                Distress score {prop.financial_distress_score}/10 — may come to market below market rate.
                {prop.dissolution_notice?" Dissolution notice on file.":""}
                {prop.has_mortgage_charge?" Mortgage charge registered.":""}
              </p>
            </div>
          )}

          <div className="analysis">
            <div className="analysis-head">
              <h3>AI Analysis</h3>
              <button className="btn-sm" style={{fontSize:"0.72rem"}} onClick={doStream} disabled={streaming}>
                <RefreshCw size={11} className={streaming?"spin":""}/> {streaming?"Analysing…":"Refresh"}
              </button>
            </div>
            <div className="analysis-body">
              <p className="analysis-streaming">
                {stream||prop.ai_summary||"Click Refresh to generate an AI analysis of this property."}
                {streaming&&<span className="cursor"/>}
              </p>

              <div className="stat-grid">
                {prop.renovation_cost_low&&<div className="stat"><div className="stat__label">Est. renovation</div><div className="stat__val">£{Math.round(prop.renovation_cost_low/1000)}k–£{Math.round((prop.renovation_cost_high||prop.renovation_cost_low)/1000)}k</div></div>}
                {prop.crime_score!=null&&<div className={`stat${prop.crime_score>=7?" highlight":prop.crime_score<4?" alert":""}`}><div className="stat__label">Safety score</div><div className="stat__val">{prop.crime_score?.toFixed(1)}/10</div></div>}
                {prop.transport_score!=null&&<div className="stat"><div className="stat__label">Transport</div><div className="stat__val">{prop.transport_score?.toFixed(1)}/10</div></div>}
                {prop.ai_score!=null&&<div className={`stat${prop.ai_score>=7?" highlight":prop.ai_score<4?" alert":""}`}><div className="stat__label">Conversion score</div><div className="stat__val">{prop.ai_score}/10</div></div>}
              </div>

              {aiUses.length>0&&(
                <div style={{marginTop:16}}>
                  <p style={{fontSize:"0.68rem",letterSpacing:".08em",textTransform:"uppercase",color:"var(--mid)",marginBottom:8}}>Suggested uses</p>
                  <div className="card-features">{aiUses.map((u:string)=><span key={u} className="feat">{u}</span>)}</div>
                </div>
              )}

              {aiRisks.length>0&&(
                <div style={{marginTop:16}}>
                  <p style={{fontSize:"0.68rem",letterSpacing:".08em",textTransform:"uppercase",color:"var(--mid)",marginBottom:8}}>Key risks</p>
                  {aiRisks.map((r:string)=>(
                    <div key={r} style={{display:"flex",gap:8,fontSize:"0.78rem",color:"var(--mid)",padding:"4px 0",borderBottom:"1px solid var(--rule-soft)"}}>
                      <span style={{color:"var(--red)",flexShrink:0}}>—</span>{r}
                    </div>
                  ))}
                </div>
              )}

              {prop.ai_roi&&(
                <p style={{marginTop:16,fontSize:"0.82rem",lineHeight:1.65,color:"var(--ink-soft)",padding:"12px 14px",background:"var(--off-white)",borderRadius:"var(--r)",borderLeft:"2px solid var(--green)"}}>
                  {prop.ai_roi}
                </p>
              )}
            </div>
          </div>

          {ai.recommended_professionals?.length>0&&(
            <div className="analysis" style={{marginTop:16}}>
              <div className="analysis-head"><h3>Who you'll need</h3></div>
              <div className="analysis-body">
                <div className="pros">
                  {ai.recommended_professionals.map((p:any)=>(
                    <div key={p.role} className="pro">
                      <div className={`pro__dot ${p.urgency||"low"}`}/>
                      <div>
                        <div className="pro__role">{p.role}</div>
                        <div className="pro__why">{p.reason||p.why}</div>
                        {p.avg_cost&&<div className="pro__cost">Typical cost: {p.avg_cost}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="sidebar">
          <div className="sidebar-box">
            <div className="sidebar-box-head">Quick actions</div>
            <div className="sidebar-box-body" style={{display:"flex",flexDirection:"column",gap:8}}>
              <button className="btn btn-black" style={{width:"100%",justifyContent:"center"}} onClick={()=>setModal(true)}><Mail size={13}/> Express interest</button>
              <button className="btn btn-outline" style={{width:"100%",justifyContent:"center"}} onClick={()=>favMut.mutate()}><Heart size={13} fill={faved?"currentColor":"none"}/> {faved?"Remove from saved":"Save property"}</button>
              <a href={prop.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{width:"100%",justifyContent:"center"}}><ExternalLink size={13}/> View original</a>
            </div>
          </div>

          <div className="sidebar-box">
            <div className="sidebar-box-head">Property details</div>
            <div className="sidebar-box-body">
              {[
                ["Source",      prop.source],
                ["Type",        prop.listing_type],
                ["County",      prop.county],
                ["Postcode",    prop.postcode],
                ["Listed",      prop.is_listed?`Yes — Grade ${prop.listed_grade}`:"No"],
                ["Conservation",prop.in_conservation?"Yes":"No"],
                ["Floor area",  prop.floor_area_sqft?`${prop.floor_area_sqft.toLocaleString()} sqft`:null],
                ["Acreage",     prop.acreage?`${prop.acreage} acres`:null],
                ["First seen",  formatDistanceToNow(new Date(prop.first_seen),{addSuffix:true})],
              ].filter(([,v])=>v).map(([l,v])=>(
                <div key={l as string} style={{display:"flex",justifyContent:"space-between",fontSize:"0.78rem",padding:"6px 0",borderBottom:"1px solid var(--rule-soft)"}}>
                  <span style={{color:"var(--mid)"}}>{l}</span>
                  <span style={{fontWeight:500,textAlign:"right",maxWidth:"60%"}}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {modal&&<InterestModal property={prop} onClose={()=>setModal(false)} onSent={()=>setModal(false)}/>}
    </div>
  );
}
