import { useSEO } from "../hooks/useSEO";
import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Heart, ExternalLink, RefreshCw, Mail, ChevronLeft, ChevronRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { propertyApi, favouritesApi } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import { buildCriteria, computeMatchScore } from "../components/property/PropertyCard";
import InterestModal from "../components/ui/InterestModal";
import { cleanDescription } from "../utils/text";

const FEATS: [string, string, string][] = [
  ["has_parking","🅿️","Parking"],["has_graveyard","⚰️","Graveyard"],
  ["has_hall","🏛","Hall"],["has_spire","⛪","Spire"],
  ["has_organ","🎵","Organ"],["has_vestry","📦","Vestry"],
];

function HeroSlideshow({ images, title }: { images: string[]; title: string }) {
  const [idx, setIdx] = useState(0);
  const [failed, setFailed] = useState<Set<number>>(new Set());
  const valid = images.filter((_, i) => !failed.has(i));
  if (valid.length === 0) return null;
  const cur = idx % valid.length;
  const handleError = () => {
    const origIdx = images.indexOf(valid[cur]);
    setFailed(prev => new Set(prev).add(origIdx));
  };
  const prev = (e: React.MouseEvent) => { e.stopPropagation(); setIdx(i => (i - 1 + valid.length) % valid.length); };
  const next = (e: React.MouseEvent) => { e.stopPropagation(); setIdx(i => (i + 1) % valid.length); };

  return (
    <div style={{ position: "relative", borderRadius: 18, overflow: "hidden", marginBottom: 28, height: 360, background: "var(--surface2)" }}>
      <img key={valid[cur]} src={valid[cur]} alt={title} onError={handleError}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      {valid.length > 1 && (
        <>
          <button onClick={prev} style={{ position:"absolute", left:14, top:"50%", transform:"translateY(-50%)", background:"rgba(0,0,0,.45)", backdropFilter:"blur(8px)", color:"#fff", border:"none", borderRadius:"50%", width:38, height:38, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <ChevronLeft size={18} />
          </button>
          <button onClick={next} style={{ position:"absolute", right:14, top:"50%", transform:"translateY(-50%)", background:"rgba(0,0,0,.45)", backdropFilter:"blur(8px)", color:"#fff", border:"none", borderRadius:"50%", width:38, height:38, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <ChevronRight size={18} />
          </button>
          <div style={{ position:"absolute", bottom:14, left:"50%", transform:"translateX(-50%)", display:"flex", gap:6 }}>
            {valid.map((_: string, i: number) => (
              <span key={i} onClick={e => { e.stopPropagation(); setIdx(i); }} style={{ width:7, height:7, borderRadius:"50%", cursor:"pointer", display:"inline-block", background: i===cur ? "#fff" : "rgba(255,255,255,.4)", boxShadow:"0 1px 3px rgba(0,0,0,.3)" }} />
            ))}
          </div>
          <div style={{ position:"absolute", top:14, right:14, background:"rgba(0,0,0,.45)", backdropFilter:"blur(8px)", color:"#fff", fontSize:"0.72rem", fontWeight:600, padding:"3px 10px", borderRadius:20 }}>
            {cur + 1} / {valid.length}
          </div>
        </>
      )}
    </div>
  );
}

function MatchBreakdown({ criteria, score }: { criteria: any[]; score: number }) {
  const scoreColor = score >= 90 ? "#1a7a3c" : score >= 70 ? "#7a6f1a" : score >= 50 ? "#b84a15" : "#8b8b8b";
  const exact = criteria.filter(c => c.status === "exact").length;
  const close = criteria.filter(c => c.status === "close").length;
  const miss  = criteria.filter(c => c.status === "miss").length;
  return (
    <div style={{ background:"var(--surface)", border:"1px solid var(--line)", borderRadius:18, overflow:"hidden", marginBottom:12 }}>
      <div style={{ padding:"12px 18px", borderBottom:"1px solid var(--line)", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ font:"600 12px 'Space Grotesk'", letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink3)" }}>Search match</span>
        <span style={{ fontFamily:"'Gabarito'", fontSize:"1.2rem", fontWeight:900, color:scoreColor }}>{score}%</span>
      </div>
      <div style={{ padding:"14px 18px" }}>
        <div style={{ display:"flex", gap:0, marginBottom:14, borderRadius:10, overflow:"hidden", border:"1px solid var(--line)" }}>
          {[
            { label:"Exact", count:exact, color:"#1a7a3c" },
            { label:"Close", count:close, color:"#f5a623" },
            { label:"Miss",  count:miss,  color:"var(--mid)" },
          ].map(s => (
            <div key={s.label} style={{ flex:1, padding:"8px 0", textAlign:"center", borderRight:"1px solid var(--line)" }}>
              <div style={{ fontFamily:"'Gabarito'", fontSize:"1rem", fontWeight:900, color:s.color }}>{s.count}</div>
              <div style={{ fontSize:"0.58rem", letterSpacing:".06em", textTransform:"uppercase", color:"var(--ink3)" }}>{s.label}</div>
            </div>
          ))}
        </div>
        {criteria.map((c, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:8, fontSize:"0.78rem", padding:"5px 0", borderBottom:"1px solid var(--line3)" }}>
            <span style={{ width:7, height:7, borderRadius:"50%", flexShrink:0, background: c.status==="exact" ? "#1a7a3c" : c.status==="close" ? "#f5a623" : "var(--rule)", display:"inline-block" }} />
            <span style={{ color: c.status==="miss" ? "var(--ink3)" : "var(--ink)" }}>{c.label}</span>
            {c.detail && <span style={{ marginLeft:"auto", color:"var(--ink3)", fontSize:"0.72rem" }}>{c.detail}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function SidebarCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background:"var(--surface)", border:"1px solid var(--line)", borderRadius:18, overflow:"hidden", marginBottom:12 }}>
      <div style={{ padding:"11px 18px", borderBottom:"1px solid var(--line)", font:"600 11px 'Space Grotesk'", letterSpacing:"0.1em", textTransform:"uppercase", color:"var(--ink3)" }}>{title}</div>
      <div style={{ padding:"16px 18px" }}>{children}</div>
    </div>
  );
}

export default function PropertyPage() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc       = useQueryClient();
  const { intent } = useSearchStore();

  const [faved,     setFaved]     = useState(false);
  const [modal,     setModal]     = useState(false);
  const [stream,    setStream]    = useState("");
  const [streaming, setStreaming] = useState(false);
  const didStream = useRef(false);

  const { data: prop, isLoading } = useQuery({
    queryKey: ["property", id],
    queryFn:  () => propertyApi.get(id!),
    enabled:  !!id,
  });

  useSEO({
    title: prop ? `${prop.title} — Nave` : "Property — Nave",
    description: prop?.description?.slice(0, 160) ?? "Church and chapel property on Nave.",
  });

  const favMut = useMutation({
    mutationFn: () => faved ? favouritesApi.remove(id!) : favouritesApi.add(id!),
    onSuccess:  () => { setFaved(f => !f); qc.invalidateQueries({ queryKey: ["favourites"] }); },
  });

  useEffect(() => {
    if (prop && !didStream.current) { didStream.current = true; doStream(); }
  }, [prop]);

  async function doStream() {
    setStream(""); setStreaming(true);
    try {
      const res = await fetch(`/api/search/stream-analysis/${id}`);
      if (!res.body) return;
      const reader = res.body.getReader();
      const dec    = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value);
        setStream(buf);
      }
    } catch (e) { console.error("Stream error:", e); }
    finally { setStreaming(false); }
  }

  if (isLoading) return (
    <div className="wrap detail">
      <div className="skeleton" style={{ height:360, borderRadius:18, marginBottom:24 }} />
      <div className="skeleton" style={{ height:40, width:"60%", marginBottom:12 }} />
      <div className="skeleton" style={{ height:24, width:"40%" }} />
    </div>
  );

  if (!prop) return (
    <div className="wrap detail" style={{ textAlign:"center", paddingTop:80 }}>
      <p style={{ color:"var(--ink3)", marginBottom:16 }}>Property not found.</p>
      <button onClick={() => navigate(-1)} style={{ background:"var(--btnbg)", color:"var(--btnfg)", border:"none", borderRadius:980, padding:"10px 22px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>← Go back</button>
    </div>
  );

  const imgs: string[] = Array.isArray(prop.images) && prop.images.length > 0
    ? prop.images : prop.image_url ? [prop.image_url] : [];

  const feats      = FEATS.filter(([k]) => (prop as any)[k]);
  const criteria   = buildCriteria(prop, intent);
  const matchScore = computeMatchScore(criteria);

  return (
    <div style={{ background:"var(--bg)", minHeight:"calc(100svh - 52px)" }}>
      <div className="wrap detail">

        {/* Back button */}
        <button onClick={() => navigate(-1)} style={{ display:"inline-flex", alignItems:"center", gap:6, fontSize:"0.78rem", color:"var(--ink3)", background:"none", border:"none", cursor:"pointer", marginBottom:20, padding:0, transition:"color .15s" }}
          onMouseEnter={e => (e.currentTarget.style.color="var(--ink)")}
          onMouseLeave={e => (e.currentTarget.style.color="var(--ink3)")}
        >
          <ArrowLeft size={13} /> Back to results
        </button>

        {/* Hero slideshow */}
        {imgs.length > 0 && <HeroSlideshow images={imgs} title={prop.title} />}

        <div className="detail-grid">

          {/* ── Left column ── */}
          <div>
            {/* Source badge */}
            <p style={{ font:"500 11px 'Space Grotesk'", letterSpacing:"0.12em", textTransform:"uppercase", color:"var(--ink3)", marginBottom:10 }}>{prop.source}</p>

            {/* Title */}
            <h1 style={{ fontFamily:"'Gabarito'", fontWeight:900, fontSize:"clamp(1.4rem, 3vw, 2.2rem)", lineHeight:1.1, letterSpacing:"-0.03em", color:"var(--ink)", marginBottom:14 }}>{prop.title}</h1>

            {/* Price */}
            <p style={{ fontFamily:"'Gabarito'", fontSize:"1.8rem", fontWeight:700, letterSpacing:"-0.03em", color:"var(--ink)", marginBottom:12 }}>{prop.price_raw || prop.price || "POA"}</p>

            {/* Meta row */}
            <div style={{ display:"flex", flexWrap:"wrap", gap:"8px 16px", fontSize:"0.8rem", color:"var(--ink3)", marginBottom:18 }}>
              <span>📍 {prop.location}</span>
              {prop.county   && <span>{prop.county}</span>}
              {prop.postcode && <span>{prop.postcode}</span>}
              <span>{formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })}</span>
            </div>

            {/* Tags */}
            <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:18 }}>
              {prop.is_listed && <span className="tag heritage">Grade {prop.listed_grade} Listed</span>}
              {prop.listing_type === "auction" && <span className="tag auction">Auction</span>}
            </div>

            {/* Features */}
            {feats.length > 0 && (
              <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:22 }}>
                {feats.map(([, icon, label]) => (
                  <span key={label} style={{ fontSize:"0.72rem", padding:"4px 10px", border:"1px solid var(--line)", borderRadius:8, color:"var(--ink2)", background:"var(--surface2)", display:"inline-flex", alignItems:"center", gap:5 }}>{icon} {label}</span>
                ))}
              </div>
            )}

            {/* CTAs */}
            <div style={{ display:"flex", gap:8, marginBottom:28, flexWrap:"wrap" }}>
              <a href={prop.source_url || prop.url} target="_blank" rel="noopener noreferrer"
                style={{ display:"inline-flex", alignItems:"center", gap:6, background:"var(--btnbg)", color:"var(--btnfg)", border:"none", borderRadius:980, padding:"11px 22px", font:"500 14px 'Space Grotesk'", cursor:"pointer", textDecoration:"none" }}>
                <ExternalLink size={13} /> View on {prop.source}
              </a>
              <button onClick={() => favMut.mutate()}
                style={{ display:"inline-flex", alignItems:"center", gap:6, background:"var(--surface)", color:"var(--ink)", border:"1px solid var(--line)", borderRadius:980, padding:"11px 22px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>
                <Heart size={13} fill={faved ? "currentColor" : "none"} />
                {faved ? "Saved" : "Save"}
              </button>
              <button onClick={() => setModal(true)}
                style={{ display:"inline-flex", alignItems:"center", gap:6, background:"var(--surface)", color:"var(--ink)", border:"1px solid var(--line)", borderRadius:980, padding:"11px 22px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>
                <Mail size={13} /> Express interest
              </button>
            </div>

            {/* Description */}
            {prop.description && (
              <p style={{ fontSize:"0.88rem", lineHeight:1.75, color:"var(--ink2)", marginBottom:28, whiteSpace:"pre-wrap" }}>
                {cleanDescription(prop.description)}
              </p>
            )}

            {/* AI analysis */}
            <div style={{ background:"var(--surface)", border:"1px solid var(--line)", borderRadius:18, overflow:"hidden", marginBottom:16 }}>
              <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--line)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <h3 style={{ fontFamily:"'Gabarito'", fontSize:"0.95rem", fontWeight:700, color:"var(--ink)", margin:0 }}>About this property</h3>
                <button onClick={doStream} disabled={streaming}
                  style={{ display:"inline-flex", alignItems:"center", gap:5, fontSize:"0.72rem", color:"var(--ink3)", background:"var(--surface2)", border:"1px solid var(--line)", borderRadius:980, padding:"5px 12px", cursor:"pointer" }}>
                  <RefreshCw size={11} className={streaming ? "spin" : ""} />
                  {streaming ? "Analysing…" : "Refresh"}
                </button>
              </div>
              <div style={{ padding:"18px 20px" }}>
                <p style={{ fontSize:"0.85rem", lineHeight:1.75, color:"var(--ink2)", margin:0 }}>
                  {stream || "Analysis will appear here automatically."}
                  {streaming && <span className="cursor" />}
                </p>
              </div>
            </div>
          </div>

          {/* ── Sidebar ── */}
          <div className="sidebar">

            {criteria.length > 0 && (
              <MatchBreakdown criteria={criteria} score={matchScore} />
            )}

            <SidebarCard title="Quick actions">
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                <button onClick={() => setModal(true)}
                  style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"center", gap:6, background:"var(--btnbg)", color:"var(--btnfg)", border:"none", borderRadius:980, padding:"11px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>
                  <Mail size={13} /> Express interest
                </button>
                <button onClick={() => favMut.mutate()}
                  style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"center", gap:6, background:"var(--surface2)", color:"var(--ink)", border:"1px solid var(--line)", borderRadius:980, padding:"11px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>
                  <Heart size={13} fill={faved ? "currentColor" : "none"} />
                  {faved ? "Remove from saved" : "Save property"}
                </button>
                <a href={prop.source_url || prop.url} target="_blank" rel="noopener noreferrer"
                  style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"center", gap:6, background:"var(--surface2)", color:"var(--ink)", border:"1px solid var(--line)", borderRadius:980, padding:"11px", font:"500 14px 'Space Grotesk'", cursor:"pointer", textDecoration:"none" }}>
                  <ExternalLink size={13} /> View original listing
                </a>
              </div>
            </SidebarCard>

            <SidebarCard title="Property details">
              {[
                ["Source",     prop.source],
                ["Type",       prop.listing_type],
                ["Location",   prop.location],
                ["County",     prop.county],
                ["Postcode",   prop.postcode],
                ["Listed",     prop.is_listed ? `Yes — Grade ${prop.listed_grade}` : null],
                ["First seen", formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })],
              ].filter(([, v]) => v).map(([l, v]) => (
                <div key={l as string} style={{ display:"flex", justifyContent:"space-between", fontSize:"0.78rem", padding:"6px 0", borderBottom:"1px solid var(--line3)" }}>
                  <span style={{ color:"var(--ink3)" }}>{l}</span>
                  <span style={{ fontWeight:500, textAlign:"right", maxWidth:"60%", color:"var(--ink)" }}>{v}</span>
                </div>
              ))}
            </SidebarCard>

          </div>
        </div>
      </div>

      {modal && (
        <InterestModal
          property={prop}
          onClose={() => setModal(false)}
          onSent={() => setModal(false)}
        />
      )}
    </div>
  );
}