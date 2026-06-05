import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Heart, ExternalLink, RefreshCw, AlertTriangle, Mail } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { propertyApi, favouritesApi } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import { buildCriteria, computeMatchScore } from "../components/property/PropertyCard";
import InterestModal from "../components/ui/InterestModal";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const FEATS: [string, string, string][] = [
  ["has_parking","🅿️","Parking"],["has_graveyard","⚰️","Graveyard"],
  ["has_balcony","🪟","Balcony"],["has_porch","🚪","Porch"],
  ["has_hall","🏛","Hall"],["has_spire","⛪","Spire"],
  ["has_organ","🎵","Organ"],["has_vestry","📦","Vestry"],
];

function MatchBreakdown({ criteria, score }: { criteria: any[]; score: number }) {
  const scoreStr = score >= 95 ? "100" : score >= 85 ? "90" : score >= 75 ? "80" : score >= 65 ? "70" : score >= 50 ? "60" : "30";
  const scoreColor =
    score >= 90 ? "#1a7a3c" : score >= 70 ? "#7a6f1a" : score >= 50 ? "#b84a15" : "#8b8b8b";

  const exact = criteria.filter(c => c.status === "exact").length;
  const close = criteria.filter(c => c.status === "close").length;
  const miss  = criteria.filter(c => c.status === "miss").length;

  return (
    <div className="match-breakdown">
      <div className="match-breakdown-head">
        <h3>Search match</h3>
        <span className="match-score-big" style={{ color: scoreColor }}>{score}%</span>
      </div>
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--rule)" }}>
        {[
          { label: "Exact", count: exact, color: "#1a7a3c" },
          { label: "Close", count: close, color: "#f5a623" },
          { label: "Miss",  count: miss,  color: "var(--rule)" },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, padding: "10px 0", textAlign: "center", borderRight: "1px solid var(--rule-soft)" }}>
            <div style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem", fontWeight: 900, color: s.color }}>{s.count}</div>
            <div style={{ fontSize: "0.62rem", letterSpacing: ".06em", textTransform: "uppercase", color: "var(--mid)", marginTop: 1 }}>{s.label}</div>
          </div>
        ))}
      </div>
      <div className="match-rows">
        {criteria.map((c, i) => (
          <div key={i} className="match-row">
            <div className={`match-row-dot ${c.status}`} />
            <span className={`match-row-label ${c.status === "miss" ? "miss" : ""}`}>{c.label}</span>
            {c.detail && <span className="match-row-value">{c.detail}</span>}
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

  const [faved,    setFaved]    = useState(false);
  const [modal,    setModal]    = useState(false);
  const [stream,   setStream]   = useState("");
  const [streaming,setStreaming]= useState(false);
  const [imgErr,   setImgErr]   = useState(false);
  const didStream = useRef(false);

  const { data: prop, isLoading } = useQuery({
    queryKey: ["property", id],
    queryFn:  () => propertyApi.get(id!),
    enabled:  !!id,
  });

  const { data: analysis } = useQuery({
    queryKey: ["analysis", id],
    queryFn:  () => propertyApi.analysis(id!),
    enabled:  !!id,
    staleTime: Infinity,
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
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split("\n")) {
          if (line.startsWith("data: ")) {
            const d = line.slice(6);
            if (d === "[DONE]") break;
            try { const parsed = JSON.parse(d); if (parsed.text) setStream(t => t + parsed.text); } catch {}
          }
        }
      }
    } finally { setStreaming(false); }
  }

  if (isLoading) return (
    <div className="wrap detail">
      <div className="skeleton" style={{ height: 400, borderRadius: "var(--r2)" }} />
    </div>
  );
  if (!prop) return (
    <div className="wrap detail" style={{ textAlign: "center" }}>
      <p style={{ color: "var(--mid)" }}>Property not found. <button className="btn btn-ghost" onClick={() => navigate(-1)}>Go back</button></p>
    </div>
  );

  const feats    = FEATS.filter(([k]) => (prop as any)[k]);
  const ai       = analysis?.analysis ?? {};
  const aiUses   = (() => { try { return JSON.parse(prop.ai_uses || "[]"); } catch { return []; } })();
  const aiRisks  = (() => { try { return JSON.parse(prop.ai_risks || "[]"); } catch { return []; } })();
  const imgUrl   = prop.image_url || prop.images?.[0] || null;

  // Build match criteria for this property from the search intent
  const criteria = buildCriteria(prop, intent);
  const matchScore = computeMatchScore(criteria);

  return (
    <div className="wrap detail">
      <button className="detail-back" onClick={() => navigate(-1)}>
        <ArrowLeft size={13} /> Back to results
      </button>

      {/* Hero image */}
      {imgUrl && !imgErr && (
        <div style={{ borderRadius: "var(--r2)", overflow: "hidden", marginBottom: 28, height: 280 }}>
          <img
            src={imgUrl} alt={prop.title}
            onError={() => setImgErr(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      <div className="detail-grid">

        {/* ── Left ─────────────────────────────────────────────────────── */}
        <div>
          <p className="detail-source">{prop.source}</p>
          <h1 className="detail-title">{prop.title}</h1>
          <p className="detail-price">{prop.price_raw || "POA"}</p>

          <div className="detail-meta">
            <span>📍 {prop.location}</span>
            {prop.county   && <span>{prop.county}</span>}
            {prop.postcode && <span>{prop.postcode}</span>}
            <span>{formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })}</span>
          </div>

          <div className="detail-flags">
            {prop.is_listed          && <span className="tag">Grade {prop.listed_grade} Listed</span>}
            {prop.in_conservation    && <span className="tag">Conservation Area</span>}
            {prop.heritage_at_risk   && <span className="tag heritage">Heritage at Risk</span>}
            {prop.dissolution_notice && <span className="tag signal">Dissolution Notice</span>}
            {prop.has_mortgage_charge&& <span className="tag signal">Mortgage Charge</span>}
            {prop.listing_type === "auction" && <span className="tag auction">Auction</span>}
          </div>

          {feats.length > 0 && (
            <div className="card-features" style={{ marginBottom: 20 }}>
              {feats.map(([, icon, label]) => <span key={label} className="feat">{icon} {label}</span>)}
              {prop.acreage         && <span className="feat">📐 {prop.acreage} acres</span>}
              {prop.floor_area_sqft && <span className="feat">📏 {prop.floor_area_sqft.toLocaleString()} sqft</span>}
            </div>
          )}

          {/* CTAs */}
          <div style={{ display: "flex", gap: 8, marginBottom: 28, flexWrap: "wrap" }}>
            <a href={prop.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-black">
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

          {prop.description && <p className="detail-desc">{prop.description}</p>}

          {/* Distress signals */}
          {prop.financial_distress_score > 4 && (
            <div style={{ padding: "14px 16px", border: "1px solid rgba(245,166,35,.4)", borderLeft: "3px solid var(--yellow)", borderRadius: "var(--r2)", marginBottom: 24, background: "rgba(245,166,35,.04)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <AlertTriangle size={14} color="var(--yellow)" />
                <strong style={{ fontSize: "0.83rem" }}>Financial distress signals detected</strong>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--mid)", lineHeight: 1.55 }}>
                Distress score {prop.financial_distress_score}/10 — may come to market below market rate.
                {prop.dissolution_notice   ? " Dissolution notice on file." : ""}
                {prop.has_mortgage_charge  ? " Mortgage charge registered." : ""}
              </p>
            </div>
          )}

          {/* AI narrative */}
          <div className="analysis">
            <div className="analysis-head">
              <h3>How this matches your search</h3>
              <button className="btn-sm" style={{ fontSize: "0.72rem" }} onClick={doStream} disabled={streaming}>
                <RefreshCw size={11} className={streaming ? "spin" : ""} />
                {streaming ? "Analysing…" : "Refresh"}
              </button>
            </div>
            <div className="analysis-body">
              <p className="analysis-streaming">
                {stream || prop.ai_summary || "Click Refresh to generate an AI analysis."}
                {streaming && <span className="cursor" />}
              </p>

              <div className="stat-grid">
                {prop.renovation_cost_low && (
                  <div className="stat">
                    <div className="stat__label">Est. renovation</div>
                    <div className="stat__val">£{Math.round(prop.renovation_cost_low/1000)}k–£{Math.round((prop.renovation_cost_high||prop.renovation_cost_low)/1000)}k</div>
                  </div>
                )}
                {prop.crime_score != null && (
                  <div className={`stat ${prop.crime_score >= 7 ? "highlight" : prop.crime_score < 4 ? "alert" : ""}`}>
                    <div className="stat__label">Safety score</div>
                    <div className="stat__val">{prop.crime_score?.toFixed(1)}/10</div>
                  </div>
                )}
                {prop.transport_score != null && (
                  <div className="stat">
                    <div className="stat__label">Transport</div>
                    <div className="stat__val">{prop.transport_score?.toFixed(1)}/10</div>
                  </div>
                )}
                {prop.ai_score != null && (
                  <div className={`stat ${prop.ai_score >= 7 ? "highlight" : prop.ai_score < 4 ? "alert" : ""}`}>
                    <div className="stat__label">Conversion score</div>
                    <div className="stat__val">{prop.ai_score}/10</div>
                  </div>
                )}
              </div>

              {aiUses.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <p style={{ fontSize: "0.68rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--mid)", marginBottom: 8 }}>Suggested uses</p>
                  <div className="card-features">{aiUses.map((u: string) => <span key={u} className="feat">{u}</span>)}</div>
                </div>
              )}

              {aiRisks.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <p style={{ fontSize: "0.68rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--mid)", marginBottom: 8 }}>Key risks</p>
                  {aiRisks.map((r: string) => (
                    <div key={r} style={{ display: "flex", gap: 8, fontSize: "0.78rem", color: "var(--mid)", padding: "4px 0", borderBottom: "1px solid var(--rule-soft)" }}>
                      <span style={{ color: "var(--red)", flexShrink: 0 }}>—</span>{r}
                    </div>
                  ))}
                </div>
              )}

              {prop.ai_roi && (
                <p style={{ marginTop: 16, fontSize: "0.82rem", lineHeight: 1.65, color: "var(--ink-soft)", padding: "12px 14px", background: "var(--off-white)", borderRadius: "var(--r)", borderLeft: "2px solid var(--green)" }}>
                  {prop.ai_roi}
                </p>
              )}
            </div>
          </div>

          {/* Recommended professionals */}
          {ai.recommended_professionals?.length > 0 && (
            <div className="analysis" style={{ marginTop: 16 }}>
              <div className="analysis-head"><h3>Who you'll need</h3></div>
              <div className="analysis-body">
                <div className="pros">
                  {ai.recommended_professionals.map((prof: any) => (
                    <div key={prof.role} className="pro">
                      <div className={`pro__dot ${prof.urgency || "low"}`} />
                      <div>
                        <div className="pro__role">{prof.role}</div>
                        <div className="pro__why">{prof.reason || prof.why}</div>
                        {prof.avg_cost && <div className="pro__cost">Typical cost: {prof.avg_cost}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <div className="sidebar">

          {/* Match breakdown */}
          {criteria.length > 0 && (
            <MatchBreakdown criteria={criteria} score={matchScore} />
          )}

          {/* Favourite + contact */}
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
              <a href={prop.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{ width: "100%", justifyContent: "center" }}>
                <ExternalLink size={13} /> View original listing
              </a>
            </div>
          </div>

          {/* Property details */}
          <div className="sidebar-box">
            <div className="sidebar-box-head">Property details</div>
            <div className="sidebar-box-body">
              {[
                ["Source",       prop.source],
                ["Type",         prop.listing_type],
                ["County",       prop.county],
                ["Postcode",     prop.postcode],
                ["Listed",       prop.is_listed ? `Yes — Grade ${prop.listed_grade}` : "No"],
                ["Conservation", prop.in_conservation ? "Yes" : "No"],
                ["Floor area",   prop.floor_area_sqft ? `${prop.floor_area_sqft.toLocaleString()} sqft` : null],
                ["Acreage",      prop.acreage ? `${prop.acreage} acres` : null],
                ["First seen",   formatDistanceToNow(new Date(prop.first_seen), { addSuffix: true })],
              ].filter(([, v]) => v).map(([l, v]) => (
                <div key={l as string} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", padding: "6px 0", borderBottom: "1px solid var(--rule-soft)" }}>
                  <span style={{ color: "var(--mid)" }}>{l}</span>
                  <span style={{ fontWeight: 500, textAlign: "right", maxWidth: "60%", color: "var(--ink)" }}>{v}</span>
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
