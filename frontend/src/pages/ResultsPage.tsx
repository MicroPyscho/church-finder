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

export default function ResultsPage() {
  const navigate = useNavigate();
  const { query, results, intent, filters, page, sortBy, setResults, setPage, setSortBy } = useSearchStore();

  const mut = useMutation({
    mutationFn: () =>
      api.post("/api/search", { query, filters, page, sort_by: sortBy }).then(r => r.data),
    onSuccess: (data) => setResults(data),
  });

  useEffect(() => { if (!query) { navigate("/"); return; } if (!results) mut.mutate(); }, []);
  useEffect(() => { if (query && results) mut.mutate(); }, [page, sortBy]);

  const props = results?.results ?? [];
  const total = results?.total ?? 0;

  // Build criteria + score for each property
  const enriched = props.map((p: any) => {
    const criteria = buildCriteria(p, intent);
    const score    = computeMatchScore(criteria);
    return { ...p, _criteria: criteria, _score: score };
  });

  // Group into bands
  function band(s: number) {
    return s >= 95 ? 100 : s >= 85 ? 90 : s >= 75 ? 80 : s >= 65 ? 70 : s >= 50 ? 60 : 30;
  }

  const hasCriteria = intent && (
    intent.price_max || intent.locations?.length ||
    intent.features?.length || intent.listing_type !== "any"
  );

  const grouped = hasCriteria
    ? BANDS.map(b => ({
        ...b,
        items: enriched.filter((p: any) => band(p._score) === b.score),
      })).filter(b => b.items.length > 0)
    : [{ score: 100, label: "Results", items: enriched }];

  return (
    <div className="results-page wrap">

      {/* Header */}
      <div className="results-header">
        <div>
          <button className="detail-back" onClick={() => navigate("/")} style={{ marginBottom: 8 }}>
            <ArrowLeft size={13} /> New search
          </button>
          <div className="results-count">
            {mut.isPending
              ? "Searching 30+ sources…"
              : <>{total.toLocaleString()} properties<span>for "{query}"</span></>}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {hasCriteria && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.72rem", color: "var(--mid)" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#1a7a3c", display: "inline-block" }} /> Exact
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#f5a623", display: "inline-block", marginLeft: 4 }} /> Close
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--rule)", display: "inline-block", marginLeft: 4 }} /> No match
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

      {/* Results */}
      {mut.isPending ? (
        <SkeletonCards count={5} />
      ) : props.length === 0 ? (
        <div className="empty">
          <div className="empty__icon">⛪</div>
          <div className="empty__title">No results found</div>
          <p className="empty__body">Try broader keywords — we show partial matches down to 30%.</p>
        </div>
      ) : (
        <>
          {grouped.map(b => (
            <div key={b.score}>
              {hasCriteria && (
                <div className="band-header"><span>{b.label}</span></div>
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
