import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import PropertyCard, { buildCriteria, computeMatchScore } from "../components/property/PropertyCard";
import SkeletonCards from "../components/ui/SkeletonCards";

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

export default function ResultsPage() {
  const navigate = useNavigate();
  const { query, results, intent, filters, page, sortBy, setResults, setPage, setSortBy } = useSearchStore();

  const mut = useMutation({
    mutationFn: () =>
      api.post("/api/search", { query, filters, page, sort_by: sortBy }).then(r => r.data),
    onSuccess: (data) => setResults(data),
  });

  useEffect(() => {
    if (!query) { navigate("/"); return; }
    mut.mutate();
  }, []);

  useEffect(() => {
    if (query && results) mut.mutate();
  }, [page, sortBy]);

  const props   = results?.results ?? [];
  const total   = results?.total   ?? 0;
  const iData   = results?.intent  ?? intent ?? {};

  // Build criteria + score for each property using the search intent
  const enriched = props.map((p: any) => {
    // Use backend-provided criteria if available, otherwise compute from intent
    const criteria = (p._criteria && p._criteria.length > 0)
      ? p._criteria
      : buildCriteria(p, iData);
    const score = (p._score && p._score !== 100)
      ? p._score
      : computeMatchScore(criteria);
    return { ...p, _criteria: criteria, _score: score };
  });

  // Group into match bands
  const hasIntent = iData.price_max || iData.locations?.length || iData.features?.length;

  const grouped = hasIntent
    ? BANDS.map(b => ({
        ...b,
        items: enriched.filter((p: any) => getBand(p._score) === b.score),
      })).filter(b => b.items.length > 0)
    : [{ score: 100, label: "Results", items: enriched }];

  // Broadening notice
  const broaden = results?.broadened && results?.broaden_reason;
  const impossible = results?.impossible_warn;

  return (
    <div className="results-page wrap">

      {/* ── Header ── */}
      <div className="results-header">
        <div>
          <button className="detail-back" onClick={() => navigate("/")} style={{ marginBottom: 8 }}>
            <ArrowLeft size={13} /> New search
          </button>
          <div className="results-count">
            {mut.isPending
              ? "Searching…"
              : <>{total.toLocaleString()} properties<span>for "{query}"</span></>}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Legend */}
          {hasIntent && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.72rem", color: "var(--mid)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#1a7a3c", display: "inline-block" }} />
                Exact
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f5a623", display: "inline-block" }} />
                Close
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--rule)", display: "inline-block" }} />
                Miss
              </span>
            </div>
          )}
          <select
            style={{ fontSize: "0.78rem", padding: "6px 10px", border: "1px solid var(--rule)", borderRadius: "var(--r)", background: "var(--white)", color: "var(--ink)", outline: "none", cursor: "pointer" }}
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

      {/* Broadening / impossible warnings */}
      {broaden && (
        <div style={{ padding: "10px 14px", border: "1px solid var(--rule)", borderLeft: "3px solid var(--blue)", borderRadius: "var(--r2)", marginBottom: 16, fontSize: "0.82rem", color: "var(--mid)" }}>
          ℹ️ {results.broaden_reason}
        </div>
      )}
      {impossible && (
        <div style={{ padding: "10px 14px", border: "1px solid rgba(245,166,35,.3)", borderLeft: "3px solid var(--yellow)", borderRadius: "var(--r2)", marginBottom: 16, fontSize: "0.82rem", color: "var(--ink-soft)" }}>
          ⚠️ {impossible}
        </div>
      )}

      {/* ── Results ── */}
      {mut.isPending ? (
        <SkeletonCards count={5} />
      ) : props.length === 0 ? (
        <div className="empty">
          <div className="empty__icon">⛪</div>
          <div className="empty__title">No results found</div>
          <p className="empty__body">Try broader keywords — we show partial matches down to 30%.</p>
          <button className="btn btn-outline" style={{ marginTop: 16 }} onClick={() => navigate("/")}>
            Try a new search
          </button>
        </div>
      ) : (
        <>
          {grouped.map(b => (
            <div key={b.score}>
              {hasIntent && b.items.length > 0 && (
                <div className="band-header">
                  <span>{b.label}</span>
                  <span style={{ fontSize: "0.65rem", marginLeft: 6, color: "var(--mid)" }}>
                    {b.items.length} {b.items.length === 1 ? "property" : "properties"}
                  </span>
                </div>
              )}
              <div className="cards">
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
              <button className="btn btn-outline" onClick={() => setPage(page - 1)} disabled={page <= 1}>← Prev</button>
              <span style={{ fontSize: "0.8rem", color: "var(--mid)" }}>Page {page} of {results.pages}</span>
              <button className="btn btn-outline" onClick={() => setPage(page + 1)} disabled={page >= results.pages}>Next →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}