import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, ExternalLink, Mail, MapPin } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { favouritesApi } from "../../api/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import InterestModal from "../ui/InterestModal";

interface Props { property:any; matchScore?:number; isFaved?:boolean; }

const SOURCE_TAG: Record<string,string> = {
  "Clive Emson Auctions":"auction","Allsop Auctions":"auction",
  "SDL Auctions":"auction","UK Auction List":"auction",
  "Heritage at Risk Register":"heritage",
  "Charities Commission (Pre-Market Signal)":"signal",
  "Planning Portal (Pre-Market Signal)":"signal",
  "Companies House (Signal)":"signal",
  "Church of England":"church","Church of Scotland":"church",
  "Church in Wales":"church","Methodist Church":"church",
  "Baptist Union":"church","Diocese of London":"church",
};

const FEATS: [string,string][] = [
  ["has_parking","🅿️"],["has_graveyard","⚰️"],["has_balcony","🪟"],
  ["has_porch","🚪"],["has_hall","🏛"],["has_spire","⛪"],
  ["has_organ","🎵"],["has_vestry","📦"],
];

export default function PropertyCard({ property:p, matchScore, isFaved=false }:Props) {
  const navigate = useNavigate();
  const qc       = useQueryClient();
  const [faved, setFaved] = useState(isFaved);
  const [modal, setModal] = useState(false);
  const [sent,  setSent]  = useState(false);

  const favMut = useMutation({
    mutationFn: () => faved ? favouritesApi.remove(p.id) : favouritesApi.add(p.id),
    onSuccess:  () => { setFaved(f=>!f); qc.invalidateQueries({queryKey:["favourites"]}); },
  });

  const tagClass = SOURCE_TAG[p.source] ?? "";
  const feats    = FEATS.filter(([k]) => p[k]);
  const ms       = matchScore ?? p.match_score ?? 100;
  const msStr    = ms >= 95 ? "100" : ms >= 85 ? "90" : ms >= 75 ? "80" : ms >= 65 ? "70" : ms >= 50 ? "60" : "30";

  if (p.is_off_market) {
    return (
      <div className="card off-market">
        <div className="card-body">
          <div className="card-title">{p.title}</div>
          <div className="card-meta"><span>{p.location}</span><strong>{p.price_raw||"POA"}</strong></div>
        </div>
        <div className="match" data-score={msStr}><span className="match__pct">{ms}%</span><span className="match__label">match</span></div>
      </div>
    );
  }

  return (
    <>
      <div className="card">
        <div className="card-body">
          <div className="card-top">
            <span className={`tag ${tagClass}`}>{p.source}</span>
            {p.is_listed && <span className="tag">Grade {p.listed_grade}</span>}
            {p.dissolution_notice && <span className="tag signal">Distress signal</span>}
          </div>

          <div className="card-title" onClick={()=>navigate(`/properties/${p.id}`)}>{p.title}</div>

          <div className="card-meta">
            <span><MapPin size={11} style={{marginRight:3}}/>{p.location}</span>
            <strong>{p.price_raw||"POA"}</strong>
            <span style={{fontSize:"0.72rem"}}>{formatDistanceToNow(new Date(p.first_seen),{addSuffix:true})}</span>
            {p.listing_type==="auction" && <span style={{color:"var(--orange)"}}>Auction</span>}
          </div>

          {feats.length>0 && (
            <div className="card-features">{feats.map(([,icon])=><span key={icon} className="feat">{icon}</span>)}</div>
          )}

          {p.description && <p className="card-desc">{p.description}</p>}

          <div className="card-actions">
            <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="btn-sm" onClick={e=>e.stopPropagation()}>
              <ExternalLink size={11}/> View
            </a>
            <button className={`btn-sm${faved?" saved":""}`} onClick={()=>favMut.mutate()} disabled={favMut.isPending}>
              <Heart size={11} fill={faved?"currentColor":"none"}/> {faved?"Saved":"Save"}
            </button>
            {sent
              ? <span style={{fontSize:"0.76rem",color:"var(--green)"}}>✓ Interest sent</span>
              : <button className="btn-sm fill" onClick={()=>setModal(true)}><Mail size={11}/> Contact</button>
            }
          </div>
        </div>

        <div className="match" data-score={msStr} onClick={()=>navigate(`/properties/${p.id}`)}>
          <span className="match__pct">{ms}%</span>
          <span className="match__label">match</span>
        </div>
      </div>

      {modal && <InterestModal property={p} onClose={()=>setModal(false)} onSent={()=>{setSent(true);setModal(false);}}/>}
    </>
  );
}
