import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, ExternalLink, Mail, MapPin, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { favouritesApi } from "../../api/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import InterestModal from "../ui/InterestModal";

interface Props {
  property:    any;
  matchScore?: number;
  criteria?:   any[];
  isFaved?:    boolean;
}

function toTitleCase(str: string): string {
  if (!str) return "";
  if (str === str.toUpperCase() && str.length > 4) {
    return str.split(" ").map(w =>
      w.length > 3
        ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
        : w.toLowerCase()
    ).join(" ");
  }
  return str;
}

function toSentenceCase(str: string): string {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

const SOURCE_TAG_TYPE: Record<string, string> = {
  "Clive Emson Auctions":        "auction",
  "Allsop Auctions":             "auction",
  "SDL Auctions":                "auction",
  "UK Auction List":             "auction",
  "EIG Property Auctions":       "auction",
  "Alex Martin Commercial":      "specialist",
  "Church of England":           "church",
  "Church of Scotland":          "church",
  "Church in Wales":             "church",
  "Methodist Church":            "church",
  "Diocese of London":           "church",
  "Church Growth Trust":         "church",
  "Churches Conservation Trust": "heritage",
  "Charities Commission":        "signal",
  "Companies House":             "signal",
  "Planning Portal":             "signal",
  "GOV.UK":                      "signal",
  "OnTheMarket":                 "portal",
  "Jitty":                       "portal",
  "OpenRent":                    "portal",
};

const TYPE_EMOJI: Record<string, string> = {
  church: "⛪", hall: "🏛", large_space: "🏢", other: "🏠",
};


export interface CriterionResult {
  label:   string;
  status:  "exact" | "close" | "miss";
  detail?: string;
}

export function buildCriteria(property: any, intent: any): CriterionResult[] {
  if (!intent) return [];
  const results: CriterionResult[] = [];
  const p = property;

  if (intent.price_max) {
    const priceStr = p.price_raw || p.price || "";
    const m = priceStr.match(/£([\d,]+)/);
    const priceVal = m ? parseInt(m[1].replace(/,/g, "")) : null;
    if (priceVal && priceVal <= intent.price_max) {
      results.push({ label: `Under £${(intent.price_max/1000).toFixed(0)}k`, status: "exact", detail: priceStr });
    } else if (priceVal && priceVal <= intent.price_max * 1.15) {
      results.push({ label: `Near £${(intent.price_max/1000).toFixed(0)}k`, status: "close", detail: priceStr });
    } else if (priceVal) {
      results.push({ label: `Over £${(intent.price_max/1000).toFixed(0)}k`, status: "miss", detail: priceStr });
    }
  }

  if (intent.locations && intent.locations.length > 0) {
    const loc = (p.location || "").toLowerCase();
    const hit = intent.locations.some((l: string) => loc.includes(l.toLowerCase()));
    results.push({ label: intent.locations[0], status: hit ? "exact" : "miss" });
  }

  for (const feat of (intent.features || [])) {
    const field = ({ parking:"has_parking", graveyard:"has_graveyard", hall:"has_hall", spire:"has_spire" } as any)[feat];
    results.push({ label: feat.charAt(0).toUpperCase()+feat.slice(1), status: (field && p[field]) ? "exact" : "miss" });
  }

  return results.slice(0, 5);
}

export function computeMatchScore(criteria: CriterionResult[]): number {
  if (!criteria.length) return 100;
  const total = criteria.length;
  const exact = criteria.filter(c => c.status === "exact").length;
  const close = criteria.filter(c => c.status === "close").length;
  const raw   = Math.round(((exact + close * 0.6) / total) * 100);
  if (raw >= 95) return 100;
  if (raw >= 85) return 90;
  if (raw >= 75) return 80;
  if (raw >= 65) return 70;
  if (raw >= 50) return 60;
  return 30;
}

export default function PropertyCard({
  property: p, matchScore, criteria = [], isFaved = false,
}: Props) {
  const navigate = useNavigate();
  const qc       = useQueryClient();
  const [faved,   setFaved]  = useState(isFaved);
  const [modal,   setModal]  = useState(false);
  const [sent,    setSent]   = useState(false);
  const [imgErr,  setImgErr] = useState(false);
  const [imgIdx,  setImgIdx] = useState(0);

  const favMut = useMutation({
    mutationFn: () => faved ? favouritesApi.remove(p.id) : favouritesApi.add(p.id),
    onSuccess: () => {
      setFaved(f => !f);
      qc.invalidateQueries({ queryKey: ["favourites"] });
    },
  });

  const ms        = matchScore ?? p._score ?? 100;
  const msStr     = ms >= 95 ? "100" : ms >= 85 ? "90" : ms >= 75 ? "80"
                  : ms >= 65 ? "70"  : ms >= 50 ? "60" : "30";
  const criteria_ = criteria.length > 0 ? criteria : (p._criteria || []);
  const imgUrl    = p.image_url || null;
  const emoji     = TYPE_EMOJI[p.property_type || "other"] || "⛪";
  const tagType   = SOURCE_TAG_TYPE[p.source] || "portal";

  const rawTitle  = (p.title || "")
    .replace(/£[\d,]+(\s*[-–]\s*£[\d,]+)?/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  const title     = toTitleCase(rawTitle) || p.title;
  const location  = toSentenceCase(p.location || "Location unknown");
  const priceRaw  = (p.price_raw || p.price || "POA")
    .replace(/([^\s])£/, "$1 £")
    .trim();
  const isPOA     = ["POA","Enquire","TBC","See article","Heritage at Risk",
    "Filing signal","Planning stage","Pre-market signal","Government disposal"]
    .some(x => priceRaw.includes(x));
  const snippet   = p.description
    ? p.description.replace(/\s+/g, " ").trim().slice(0, 130) + "…"
    : "";
  const timeAgo   = p.first_seen
    ? formatDistanceToNow(new Date(p.first_seen), { addSuffix: true })
    : "";

  // Build image array from either p.images (array) or p.image_url (string)
  const imgs: string[] = (p.images && p.images.length > 0)
    ? p.images
    : (imgUrl ? [imgUrl] : []);
  const cur = imgs.length > 0 ? Math.min(imgIdx, imgs.length - 1) : 0;

  return (
    <div>
      <div className="pcard">

        {/* ── Image panel with slideshow ── */}
        <div className="pcard-img" style={{ position: "relative" }}>
          {imgs.length === 0 || imgErr ? (
            <div className="pcard-img-placeholder">{emoji}</div>
          ) : (
            <>
              <img
                src={imgs[cur]}
                alt={title}
                onError={() => setImgErr(true)}
                loading="lazy"
                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              />
              {imgs.length > 1 && (
                <>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      setImgIdx(i => (i - 1 + imgs.length) % imgs.length);
                    }}
                    style={{
                      position: "absolute", left: 4, top: "50%",
                      transform: "translateY(-50%)",
                      background: "rgba(0,0,0,.5)", color: "#fff",
                      border: "none", borderRadius: "50%",
                      width: 22, height: 22, cursor: "pointer",
                      fontSize: "0.75rem", display: "flex",
                      alignItems: "center", justifyContent: "center",
                    }}
                  >
                    ‹
                  </button>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      setImgIdx(i => (i + 1) % imgs.length);
                    }}
                    style={{
                      position: "absolute", right: 4, top: "50%",
                      transform: "translateY(-50%)",
                      background: "rgba(0,0,0,.5)", color: "#fff",
                      border: "none", borderRadius: "50%",
                      width: 22, height: 22, cursor: "pointer",
                      fontSize: "0.75rem", display: "flex",
                      alignItems: "center", justifyContent: "center",
                    }}
                  >
                    ›
                  </button>
                  <div style={{
                    position: "absolute", bottom: 5, left: "50%",
                    transform: "translateX(-50%)", display: "flex", gap: 3,
                  }}>
                    {imgs.map((_: string, i: number) => (
                      <span
                        key={i}
                        onClick={e => { e.stopPropagation(); setImgIdx(i); }}
                        style={{
                          width: 5, height: 5, borderRadius: "50%",
                          cursor: "pointer",
                          background: i === cur ? "#fff" : "rgba(255,255,255,.4)",
                        }}
                      />
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* ── Favourite button ── */}
        <button
          className={"pcard-fav" + (faved ? " saved" : "")}
          onClick={e => { e.stopPropagation(); favMut.mutate(); }}
          title={faved ? "Remove from saved" : "Save property"}
        >
          <Heart
            size={12}
            fill={faved ? "#d4170f" : "none"}
            color={faved ? "#d4170f" : "var(--mid)"}
          />
        </button>

        {/* ── Body ── */}
        <div className="pcard-body">
          <div>

            {/* Source tag */}
            <div style={{ marginBottom: 6 }}>
              <span className={`tag ${tagType}`}>{p.source}</span>
              {p.listing_type === "auction" && (
                <span className="tag auction" style={{ marginLeft: 4 }}>Auction</span>
              )}
            </div>

            {/* Title */}
            <div
              className="pcard-title"
              onClick={() => navigate("/properties/" + p.id)}
            >
              {title}
            </div>

            {/* Location · Price · Time */}
            <div className="pcard-meta">
              <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <MapPin size={10} />{location}
              </span>
              {isPOA
                ? <span style={{ fontStyle: "italic" }}>{priceRaw}</span>
                : <strong style={{ color: "var(--ink)", fontSize: "0.8rem" }}>{priceRaw}</strong>
              }
              <span style={{ display: "flex", alignItems: "center", gap: 3, marginLeft: "auto" }}>
                <Clock size={9} />{timeAgo}
              </span>
            </div>

            {/* Criteria chips */}
            {criteria_.length > 0 && (
              <div className="pcard-criteria">
                {criteria_.map((c: any, i: number) => (
                  <span key={i} className={"criterion " + c.status}>
                    {c.status === "exact" ? "✓" : c.status === "close" ? "~" : "✗"}
                    {" "}{c.label}
                    {c.detail ? " · " + c.detail : ""}
                  </span>
                ))}
              </div>
            )}

            {/* Snippet */}
            {snippet && (
              <p className="pcard-desc">{snippet}</p>
            )}
          </div>

          {/* Actions */}
          <div className="pcard-actions">
            <button
              className="pcard-btn primary"
              onClick={() => navigate("/properties/" + p.id)}
            >
              View more
            </button>
            {sent ? (
              <span style={{ fontSize: "0.7rem", color: "var(--green)" }}>✓ Sent</span>
            ) : (
              <button className="pcard-btn" onClick={() => setModal(true)}>
                <Mail size={10} /> Contact
              </button>
            )}
            <button
              className="pcard-btn"
              onClick={e => {
                e.stopPropagation();
                window.open(p.source_url || p.url, "_blank", "noopener,noreferrer");
              }}
            >
              <ExternalLink size={10} /> Source
            </button>
          </div>
        </div>

        {/* ── Match score ── */}
        <div
          className="pcard-match"
          data-score={msStr}
          onClick={() => navigate("/properties/" + p.id)}
        >
          <span className="pcard-match__pct">{ms}%</span>
          <span className="pcard-match__label">match</span>
        </div>

      </div>

      {modal && (
        <InterestModal
          property={p}
          onClose={() => setModal(false)}
          onSent={() => { setSent(true); setModal(false); }}
        />
      )}
    </div>
  );
}