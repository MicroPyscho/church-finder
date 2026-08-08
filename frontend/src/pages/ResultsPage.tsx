import { useSEO } from "../hooks/useSEO";
import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, SlidersHorizontal } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import PropertyCard, { buildCriteria, computeMatchScore } from "../components/property/PropertyCard";
import SkeletonCards from "../components/ui/SkeletonCards";
import { useSearchParams } from "react-router-dom";

const BANDS = [
  { score: 100, label: "Perfect match"  },
  { score: 90,  label: "Near perfect"   },
  { score: 80,  label: "Strong match"   },
  { score: 70,  label: "Good match"     },
  { score: 60,  label: "Partial match"  },
  { score: 30,  label: "Loose match"    },
];

function getBand(score: number): number {
  if (score >= 95) return 100;
  if (score >= 85) return 90;
  if (score >= 75) return 80;
  if (score >= 65) return 70;
  if (score >= 50) return 60;
  return 30;
}

const SOURCES = ["Rightmove","Zoopla","Savills","Knight Frank","Auction House","Christie & Co","SDL Auctions","EHB","Bidx1","30+ more"];

export default function ResultsPage() {
  const navigate = useNavigate();
  const { query, results, intent, filters, page, sortBy, setResults, setPage, setSortBy } = useSearchStore();
  const [searchParams] = useSearchParams();

  useSEO({
    title:       query ? `${query} — Search Results` : "Search Results",
    description: `Church and chapel properties matching "${query}" across the UK.`,
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/api/search", { query, filters, page, sort_by: sortBy }).then(r => r.data),
    onSuccess: (data) => setResults(data),
  });

  useEffect(() => {
  const regionParam = searchParams.get("region");
  if (regionParam && !query) {
    const regionName = regionParam.replace(/-/g, " ");
    setQuery(`churches for sale in ${regionName}`);
  }
  if (!query && !regionParam) { navigate("/"); return; }
  mut.mutate();
}, []);

  useEffect(() => {
    if (query && results) mut.mutate();
  }, [page, sortBy]);

  const props  = results?.results ?? [];
  const total  = results?.total   ?? 0;
  const iData  = results?.intent  ?? intent ?? {};

  const enriched = props.map((p: any) => {
    const criteria = (p._criteria && p._criteria.length > 0) ? p._criteria : buildCriteria(p, iData);
    const score    = (p._score && p._score !== 100)          ? p._score    : computeMatchScore(criteria);
    return { ...p, _criteria: criteria, _score: score };
  });

  const hasIntent = iData.price_max || iData.locations?.length || iData.features?.length;

  const grouped = hasIntent
    ? BANDS.map(b => ({
        ...b,
        items: enriched.filter((p: any) => getBand(p._score) === b.score),
      })).filter(b => b.items.length > 0)
    : [{ score: 100, label: "Results", items: enriched }];

  const broaden   = results?.broadened && results?.broaden_reason;
  const impossible = results?.impossible_warn;

  return (
    <div style={{ minHeight: "calc(100svh - 52px)", background: "var(--bg)" }}>
      <div className="wrap" style={{ paddingTop: 28, paddingBottom: 80 }}>

        {/* ── Header ── */}
        <div style={{
          display: "flex", alignItems: "flex-start",
          justifyContent: "space-between", marginBottom: 28,
          gap: 16, flexWrap: "wrap",
        }}>
          <div>
            <button
              onClick={() => navigate("/")}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                fontSize: "0.78rem", color: "var(--ink3)",
                background: "none", border: "none", cursor: "pointer",
                marginBottom: 10, padding: 0,
                transition: "color .15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--ink)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--ink3)")}
            >
              <ArrowLeft size={13} /> New search
            </button>
            <h1 style={{
              fontFamily: "'Gabarito'", fontWeight: 900,
              fontSize: "clamp(22px, 3.5vw, 32px)",
              letterSpacing: "-0.03em", color: "var(--ink)", margin: 0,
              lineHeight: 1.1,
            }}>
              {mut.isPending
                ? <span style={{ color: "var(--ink3)" }}>Searching…</span>
                : <>{total.toLocaleString()} <span style={{ color: "var(--ink3)", fontWeight: 400 }}>for</span> "{query}"</>
              }
            </h1>
            {!mut.isPending && total > 0 && (
              <p style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)", margin: "6px 0 0" }}>
                Aggregated from 30+ sources · updated every 3 hours
              </p>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            {hasIntent && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.72rem", color: "var(--ink3)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#1a7a3c", display: "inline-block" }} />Exact
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#f5a623", display: "inline-block" }} />Close
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--rule)", display: "inline-block" }} />Miss
                </span>
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 7, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10, padding: "6px 10px" }}>
              <SlidersHorizontal size={13} style={{ color: "var(--ink3)" }} />
              <select
                style={{ fontSize: "0.78rem", border: "none", background: "transparent", color: "var(--ink)", outline: "none", cursor: "pointer" }}
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
              >
                <option value="relevance">Best match</option>
                <option value="price_asc">Price: low → high</option>
                <option value="price_desc">Price: high → low</option>
                <option value="date">Newest first</option>
              </select>
            </div>
          </div>
        </div>

        {/* Sources trust strip */}
        {!mut.isPending && total > 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            flexWrap: "wrap", marginBottom: 24,
            padding: "10px 16px",
            background: "var(--surface)", border: "1px solid var(--line)",
            borderRadius: 12,
          }}>
            <span style={{ font: "500 11px 'Space Grotesk'", color: "var(--ink3)", letterSpacing: "0.06em", textTransform: "uppercase", marginRight: 4 }}>Sources</span>
            {SOURCES.map(s => (
              <span key={s} style={{
                font: "400 11px 'Space Grotesk'", color: "var(--ink3)",
                background: "var(--surface2)", borderRadius: 6,
                padding: "2px 8px", whiteSpace: "nowrap",
              }}>{s}</span>
            ))}
          </div>
        )}

        {/* Broadening / impossible warnings */}
        {broaden && (
          <div style={{ padding: "10px 14px", background: "var(--surface)", border: "1px solid var(--line)", borderLeft: "3px solid var(--blue)", borderRadius: 12, marginBottom: 16, fontSize: "0.82rem", color: "var(--ink2)" }}>
            ℹ️ {results.broaden_reason}
          </div>
        )}
        {impossible && (
          <div style={{ padding: "10px 14px", background: "var(--surface)", border: "1px solid rgba(245,166,35,.3)", borderLeft: "3px solid var(--yellow)", borderRadius: 12, marginBottom: 16, fontSize: "0.82rem", color: "var(--ink2)" }}>
            ⚠️ {impossible}
          </div>
        )}

        {/* ── Results ── */}
        {mut.isPending ? (
          <SkeletonCards count={5} />
        ) : props.length === 0 ? (
          <div style={{ textAlign: "center", padding: "80px 24px" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: 16 }}>⛪</div>
            <p style={{ fontFamily: "'Gabarito'", fontWeight: 700, fontSize: 18, color: "var(--ink)", marginBottom: 8 }}>No results found</p>
            <p style={{ font: "300 15px 'Space Grotesk'", color: "var(--ink3)", maxWidth: 320, margin: "0 auto 20px" }}>Try broader keywords — we show partial matches down to 30%.</p>
            <button
              onClick={() => navigate("/")}
              style={{ background: "var(--btnbg)", color: "var(--btnfg)", border: "none", borderRadius: 980, padding: "11px 24px", font: "500 14px 'Space Grotesk'", cursor: "pointer" }}
            >Try a new search</button>
          </div>
        ) : (
          <>
            {grouped.map(b => (
              <div key={b.score}>
                {hasIntent && b.items.length > 0 && (
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "20px 0 10px",
                    fontSize: "0.68rem", fontWeight: 600,
                    letterSpacing: "0.12em", textTransform: "uppercase",
                    color: "var(--ink3)",
                  }}>
                    <span>{b.label}</span>
                    <span style={{ opacity: 0.6 }}>{b.items.length} {b.items.length === 1 ? "property" : "properties"}</span>
                    <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
                  </div>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {b.items.map((p: any) => (
                    <PropertyCard
                      key={p.id}
                      property={p}
                      matchScore={p._score}
                      criteria={p._criteria}
                    />
                  ))}
                </div>
              </div>
            ))}

            {/* Pagination */}
            {results?.pages > 1 && (
              <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "center", marginTop: 40 }}>
                <button
                  onClick={() => setPage(page - 1)} disabled={page <= 1}
                  style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 980, padding: "9px 18px", font: "500 13px 'Space Grotesk'", color: "var(--ink)", cursor: "pointer", opacity: page <= 1 ? 0.4 : 1 }}
                >← Prev</button>
                <span style={{ font: "400 13px 'Space Grotesk'", color: "var(--ink3)" }}>Page {page} of {results.pages}</span>
                <button
                  onClick={() => setPage(page + 1)} disabled={page >= results.pages}
                  style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 980, padding: "9px 18px", font: "500 13px 'Space Grotesk'", color: "var(--ink)", cursor: "pointer", opacity: page >= results.pages ? 0.4 : 1 }}
                >Next →</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}