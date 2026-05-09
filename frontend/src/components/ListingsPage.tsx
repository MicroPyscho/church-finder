import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Search, RefreshCw, ExternalLink, MapPin, PoundSterling, Clock } from "lucide-react";
import { listingsApi, type Listing } from "../api/client";
import clsx from "clsx";

const SOURCE_COLOURS: Record<string, string> = {
  "Rightmove":         "tag--blue",
  "OnTheMarket":       "tag--green",
  "Clive Emson":       "tag--amber",
  "Allsop":            "tag--red",
  "SDL":               "tag--purple",
  "Church of England": "tag--stone",
};

function sourceTag(source: string): string {
  for (const [key, cls] of Object.entries(SOURCE_COLOURS)) {
    if (source.toLowerCase().includes(key.toLowerCase())) return cls;
  }
  return "tag--stone";
}

function ListingCard({ listing }: { listing: Listing }) {
  return (
    <article className="listing-card">
      <div className="listing-card__head">
        <span className={clsx("tag", sourceTag(listing.source))}>
          {listing.source}
        </span>
        {!listing.notified && <span className="badge badge--new">NEW</span>}
      </div>

      <h2 className="listing-card__title">
        <a href={listing.url} target="_blank" rel="noopener noreferrer">
          {listing.title}
          <ExternalLink size={13} className="ext-icon" />
        </a>
      </h2>

      <div className="listing-card__meta">
        <span><MapPin size={13} /> {listing.location || "—"}</span>
        <span><PoundSterling size={13} /> {listing.price}</span>
        <span className="listing-card__time">
          <Clock size={13} />
          {formatDistanceToNow(new Date(listing.first_seen), { addSuffix: true })}
        </span>
      </div>

      {listing.description && (
        <p className="listing-card__desc">
          {listing.description.slice(0, 160)}
          {listing.description.length > 160 ? "…" : ""}
        </p>
      )}
    </article>
  );
}

export default function ListingsPage() {
  const qc      = useQueryClient();
  const [page,   setPage]   = useState(1);
  const [search, setSearch] = useState("");
  const [draft,  setDraft]  = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["listings", page, search],
    queryFn:  () => listingsApi.getPage(page, 20, search),
  });

  const crawlMutation = useMutation({
    mutationFn: listingsApi.triggerCrawl,
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ["listings"] }), 3000);
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(draft);
    setPage(1);
  }

  return (
    <div className="listings-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Church Properties</h1>
          <p className="page-subtitle">
            {data ? `${data.total} listing${data.total !== 1 ? "s" : ""} found` : "Loading…"}
          </p>
        </div>

        <button
          className={clsx("btn btn--primary", crawlMutation.isPending && "btn--loading")}
          onClick={() => crawlMutation.mutate()}
          disabled={crawlMutation.isPending}
        >
          <RefreshCw size={15} className={clsx(crawlMutation.isPending && "spin")} />
          {crawlMutation.isPending ? "Crawling…" : "Run Crawl"}
        </button>
      </div>

      {crawlMutation.isSuccess && (
        <div className="alert alert--success">
          Crawl started — new listings will appear shortly.
        </div>
      )}

      <form className="search-bar" onSubmit={handleSearch}>
        <Search size={16} className="search-bar__icon" />
        <input
          className="search-bar__input"
          placeholder="Search by title or location…"
          value={draft}
          onChange={e => setDraft(e.target.value)}
        />
        <button type="submit" className="btn btn--ghost">Search</button>
        {search && (
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => { setSearch(""); setDraft(""); setPage(1); }}
          >
            Clear
          </button>
        )}
      </form>

      {isLoading && (
        <div className="skeleton-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      )}

      {isError && (
        <div className="alert alert--error">
          Failed to load listings. Is the API running?
        </div>
      )}

      {data && data.items.length === 0 && !isLoading && (
        <div className="empty-state">
          <p>No listings yet. Run a crawl to get started.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="listings-grid">
            {data.items.map(l => <ListingCard key={l.id} listing={l} />)}
          </div>

          {data.pages > 1 && (
            <div className="pagination">
              <button
                className="btn btn--ghost"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                ← Prev
              </button>
              <span className="pagination__info">
                Page {data.page} of {data.pages}
              </span>
              <button
                className="btn btn--ghost"
                disabled={page >= data.pages}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
