import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import PropertyCard  from "../components/property/PropertyCard";
import SkeletonCards from "../components/ui/SkeletonCards";

const BANDS = [
  {score:100,label:"Perfect match"},
  {score:90, label:"Near perfect"},
  {score:80, label:"Strong match"},
  {score:70, label:"Good match"},
  {score:60, label:"Partial match"},
  {score:30, label:"Loose match"},
];

function band(s:number){ return s>=95?100:s>=85?90:s>=75?80:s>=65?70:s>=50?60:30; }

export default function ResultsPage() {
  const navigate = useNavigate();
  const { query, results, filters, page, sortBy, setResults, setPage, setSortBy } = useSearchStore();

  const mut = useMutation({
    mutationFn: () => api.post("/api/search",{query,filters,page,sort_by:sortBy}).then(r=>r.data),
    onSuccess: (data) => setResults(data),
  });

  useEffect(()=>{ if (!query){navigate("/");return;} if (!results) mut.mutate(); },[]);
  useEffect(()=>{ if (query&&results) mut.mutate(); },[page,sortBy]);

  const props = results?.results??[];
  const total = results?.total??0;

  const grouped = BANDS.map(b=>({
    ...b,
    items: props.filter((p:any)=>band(p.match_score??100)===b.score),
  })).filter(b=>b.items.length>0);

  // If no match scores (backend doesn't return them yet), show all under 100%
  const hasScores = props.some((p:any)=>p.match_score!=null);
  const displayGroups = hasScores ? grouped : [{score:100,label:"Results",items:props}];

  return (
    <div className="results-page wrap">
      <div className="results-header">
        <div>
          <button className="detail-back" onClick={()=>navigate("/")} style={{marginBottom:8}}>
            <ArrowLeft size={13}/> New search
          </button>
          <div className="results-count">
            {mut.isPending
              ? "Searching 30+ sources…"
              : <>{total.toLocaleString()} properties<span>for "{query}"</span></>}
          </div>
        </div>
        <select
          style={{fontSize:"0.78rem",padding:"6px 10px",border:"1px solid var(--rule)",borderRadius:"var(--r)",background:"var(--white)",color:"var(--ink)",outline:"none",cursor:"pointer"}}
          value={sortBy}
          onChange={e=>setSortBy(e.target.value)}
        >
          <option value="relevance">Best match</option>
          <option value="price_asc">Price: low → high</option>
          <option value="price_desc">Price: high → low</option>
          <option value="date">Newest first</option>
        </select>
      </div>

      {mut.isPending ? (
        <SkeletonCards count={6}/>
      ) : props.length===0 ? (
        <div className="empty">
          <div className="empty__icon">⛪</div>
          <div className="empty__title">No results found</div>
          <p className="empty__body">Try broader keywords — we'll show partial matches down to 30%.</p>
        </div>
      ) : (
        <>
          {displayGroups.map(b=>(
            <div key={b.score}>
              {hasScores && <div className="band-header"><span>{b.label}</span></div>}
              <div className="cards">
                {b.items.map((p:any)=><PropertyCard key={p.id} property={p} matchScore={b.score}/>)}
              </div>
            </div>
          ))}

          {results?.pages>1 && (
            <div style={{display:"flex",alignItems:"center",gap:12,justifyContent:"center",marginTop:40}}>
              <button className="btn btn-outline" onClick={()=>setPage(page-1)} disabled={page<=1}>← Prev</button>
              <span style={{fontSize:"0.8rem",color:"var(--mid)"}}>Page {page} of {results.pages}</span>
              <button className="btn btn-outline" onClick={()=>setPage(page+1)} disabled={page>=results.pages}>Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
