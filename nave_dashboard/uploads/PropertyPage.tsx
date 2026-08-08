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

const BASE = "";

const FEATS: [string, string, string][] = [
  ["has_parking","🅿️","Parking"],["has_graveyard","⚰️","Graveyard"],
  ["has_hall","🏛","Hall"],["has_spire","⛪","Spire"],
  ["has_organ","🎵","Organ"],["has_vestry","📦","Vestry"],
];

// Full-width looping slideshow for the detail page hero
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

  const prev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIdx(i => (i - 1 + valid.length) % valid.length);
  };
  const next = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIdx(i => (i + 1) % valid.length);
  };

  return (
    <div style={{ position: "relative", borderRadius: "var(--r2)", overflow: "hidden", marginBottom: 28, height: 320, background: "var(--surface)" }}>
      <img
        key={valid[cur]}
        src={valid[cur]}
        alt={title}
        onError={handleError}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />

      {valid.length > 1 && (
        <>
          <button onClick={prev} style={{
            position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
            background: "rgba(0,0,0,.5)", color: "#fff", border: "none", borderRadius: "50%",
            width: 36, height: 36, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <ChevronLeft size={18} />
          </button>
          <button onClick={next} style={{
            position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
            background: "rgba(0,0,0,.5)", color: "#fff", border: "none", borderRadius: "50%",
            width: 36, height: 36, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <ChevronRight size={18} />
          </button>

          {/* Dot indicators */}
          <div style={{ position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)", display: "flex", gap: 6 }}>
            {valid.map((_: string, i: number) => (
              <span key={i} onClick={e => { e.stopPropagation(); setIdx(i); }} style={{
                width: 8, height: 8, borderRadius: "50%", cursor: "pointer", display: "inline-block",
                background: i === cur ? "#fff" : "rgba(255,255,255,.45)",
                boxShadow: "0 1px 3px rgba(0,0,0,.3)",
              }} />
            ))}
          </div>

          {/* Counter */}
          <div style={{
            position: "absolute", top: 12, right: 12,
            background: "rgba(0,0,0,.5)", color: "#fff",
            fontSize: "0.72rem", fontWeight: 600, padding: "3px 8px", borderRadius: 4,
          }}>
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
    <div className="sidebar-box" style={{ marginBottom: 12 }}>
      <div className="sidebar-box-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>Search match</span>
        <span style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem", fontWeight: 900, color: scoreColor }}>{score}%</span>
      </div>
      <div className="sidebar-box-body">
        <div style={{ display: "flex", gap: 0, marginBottom: 12, borderRadius: "var(--r)", overflow: "hidden", border: "1px solid var(--rule-soft)" }}>
          {[
            { label: "Exact", count: exact, color: "#1a7a3c" },
            { label: "Close", count: close, color: "#f5a623" },
            { label: "Miss",  count: miss,  color: "var(--mid)" },
          ].map(s => (
            <div key={s.label} style={{ flex: 1, padding: "8px 0", textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 900, color: s.color }}>{s.count}</div>
              <div style={{ fontSize: "0.58rem", letterSpacing: ".06em", textTransform: "uppercase", color: "var(--mid)" }}>{s.label}</div>
            </div>
          ))}
        </div>
        {criteria.map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem", padding: "4px 0", borderBottom: "1px solid var(--rule-soft)" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", flexShrink: 0, background: c.status === "exact" ? "#1a7a3c" : c.status === "close" ? "#f5a623" : "var(--rule)", display: "inline-block" }} />
            <span style={{ color: c.status === "miss" ? "var(--mid)" : "var(--ink)" }}>{c.label}</span>
            {c.detail && <span style={{ marginLeft: "auto", color: "var(--mid)", fontSize: "0.72rem" }}>{c.detail}</span>}
          </div>
        ))}
      </div>
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
      const res = await fetch(`${BASE}/api/search/stream-analysis/${id}`);
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
    } catch (e) {
      console.error("Stream error:", e);
    } finally { setStreaming(false); }
  }

  if (isLoading) return (
    <div className="wrap detail">
      <div className="skeleton" style={{ height: 320, borderRadius: "var(--r2)", marginBottom: 24 }} />
      <div className="skeleton" style={{ height: 40, width: "60%", marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 24, width: "40%" }} />
    </div>
  );

  if (!prop) return (
    <div className="wrap detail" style={{ textAlign: "center", paddingTop: 80 }}>
      <p style={{ color: "var(--mid)", marginBottom: 16 }}>Property not found.</p>
      <button className="btn btn-outline" onClick={() => navigate(-1)}>← Go back</button>
    </div>
  );

  // Build image array
  const imgs: string[] = Array.isArray(prop.images) && prop.images.length > 0
    ? prop.images
    : prop.image_url ? [prop.image_url] : [];

  const feats      = FEATS.filter(([k]) => (prop as any)[k]);
  const criteria   = buildCriteria(prop, intent);
  const matchScore = computeMatchScore(criteria);

  return (
    <div className="wrap detail">
      <button className="detail-back" onClick={() => navigate(-1)}>
        <ArrowLeft size={13} /> Back to results
      </button>

      {/* Hero slideshow */}
      {imgs.length > 0 && <HeroSlideshow images={imgs} title={prop.title} />}

      <div className="detail-grid">

        {/* ── Left column ── */}
        <div>
          <p className="detail-source">{prop.source}</p>
          <h1 className="detail-title">{prop.title}</h1>
          <p className="detail-price">{prop.price_raw || prop.price || "POA"}</p>

          <div className="detail-meta">
            <span>📍 {prop.location}</span>
            {prop.county   && <span>{prop.county}</span>}
            {prop.postcode && <span>{prop.postcode}</span>}
            <span>{formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })}</span>
          </div>

          <div className="detail-flags" style={{ marginBottom: 16, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {prop.is_listed       && <span className="tag heritage">Grade {prop.listed_grade} Listed</span>}
            {prop.listing_type === "auction" && <span className="tag auction">Auction</span>}
          </div>

          {feats.length > 0 && (
            <div className="card-features" style={{ marginBottom: 20 }}>
              {feats.map(([, icon, label]) => <span key={label} className="feat">{icon} {label}</span>)}
            </div>
          )}

          {/* CTAs */}
          <div style={{ display: "flex", gap: 8, marginBottom: 28, flexWrap: "wrap" }}>
            <a href={prop.source_url || prop.url} target="_blank" rel="noopener noreferrer" className="btn btn-black">
              <ExternalLink size={13} /> View on {prop.source}
            </a>
            <button className="btn btn-outline" onClick={() => favMut.mutate()}>
              <Heart size={13} fill={faved ? "currentColor" : "none"} />
              {faved ? "Saved" : "Save"}
            </button>
            <button className="btn btn-outline" onClick={() => setModal(true)}>
              <Mail size={13} /> Express interest
            </button>
          </div>

          {prop.description && (
            <p className="detail-desc">{cleanDescription(prop.description)}</p>
          )}

          {/* AI analysis */}
          <div className="analysis">
            <div className="analysis-head">
              <h3>About this property</h3>
              <button className="btn-sm" onClick={doStream} disabled={streaming} style={{ fontSize: "0.72rem" }}>
                <RefreshCw size={11} className={streaming ? "spin" : ""} />
                {streaming ? "Analysing…" : "Refresh"}
              </button>
            </div>
            <div className="analysis-body">
              <p className="analysis-streaming">
                {stream || "Click Refresh to generate an analysis of this property."}
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

          <div className="sidebar-box">
            <div className="sidebar-box-head">Quick actions</div>
            <div className="sidebar-box-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button className="btn btn-black" style={{ width: "100%", justifyContent: "center" }} onClick={() => setModal(true)}>
                <Mail size={13} /> Express interest
              </button>
              <button className="btn btn-outline" style={{ width: "100%", justifyContent: "center" }} onClick={() => favMut.mutate()}>
                <Heart size={13} fill={faved ? "currentColor" : "none"} />
                {faved ? "Remove from saved" : "Save property"}
              </button>
              <a href={prop.source_url || prop.url} target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{ width: "100%", justifyContent: "center" }}>
                <ExternalLink size={13} /> View original listing
              </a>
            </div>
          </div>

          <div className="sidebar-box">
            <div className="sidebar-box-head">Property details</div>
            <div className="sidebar-box-body">
              {[
                ["Source",     prop.source],
                ["Type",       prop.listing_type],
                ["Location",   prop.location],
                ["County",     prop.county],
                ["Postcode",   prop.postcode],
                ["Listed",     prop.is_listed ? `Yes — Grade ${prop.listed_grade}` : null],
                ["First seen", formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })],
              ].filter(([, v]) => v).map(([l, v]) => (
                <div key={l as string} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", padding: "6px 0", borderBottom: "1px solid var(--rule-soft)" }}>
                  <span style={{ color: "var(--mid)" }}>{l}</span>
                  <span style={{ fontWeight: 500, textAlign: "right", maxWidth: "60%" }}>{v}</span>
                </div>
              ))}
            </div>
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
