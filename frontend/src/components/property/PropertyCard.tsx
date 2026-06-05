import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, ExternalLink, Mail, MapPin } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { favouritesApi } from "../../api/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import InterestModal from "../ui/InterestModal";

interface Props {
  property:    any;
  matchScore?: number;
  criteria?:   CriterionResult[];
  isFaved?:    boolean;
}

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
    if (p.price_gbp && p.price_gbp <= intent.price_max) {
      results.push({ label: "Under £" + (intent.price_max/1000).toFixed(0) + "k", status: "exact", detail: p.price_raw });
    } else if (p.price_gbp && p.price_gbp <= intent.price_max * 1.2) {
      results.push({ label: "Near £" + (intent.price_max/1000).toFixed(0) + "k", status: "close", detail: p.price_raw });
    } else if (p.price_gbp) {
      results.push({ label: "Over £" + (intent.price_max/1000).toFixed(0) + "k", status: "miss", detail: p.price_raw });
    }
  }

  if (intent.locations && intent.locations.length > 0) {
    const loc    = (p.location || "").toLowerCase();
    const county = (p.county   || "").toLowerCase();
    const hit    = intent.locations.some((l: string) =>
      loc.includes(l.toLowerCase()) || county.includes(l.toLowerCase())
    );
    results.push({ label: intent.locations[0], status: hit ? "exact" : "miss" });
  }

  const featureMap: Record<string, string> = {
    parking: "has_parking", graveyard: "has_graveyard",
    balcony: "has_balcony", porch: "has_porch",
    hall: "has_hall",       spire: "has_spire",
    organ: "has_organ",     vestry: "has_vestry",
  };

  for (const feat of (intent.features || [])) {
    const field = featureMap[feat];
    if (field) {
      results.push({
        label: feat.charAt(0).toUpperCase() + feat.slice(1),
        status: p[field] ? "exact" : "miss",
      });
    }
  }

  if (intent.listing_type && intent.listing_type !== "any") {
    results.push({
      label: intent.listing_type.charAt(0).toUpperCase() + intent.listing_type.slice(1),
      status: p.listing_type === intent.listing_type ? "exact" : "miss",
    });
  }

  if (intent.intent_type && intent.intent_type !== "explore") {
    const intentLabels: Record<string, string> = {
      buy_convert:   "Conversion potential",
      buy_preserve:  "Heritage / preserve",
      buy_use:       "Use as church",
      buy_religious: "Religious use",
    };
    const label = intentLabels[intent.intent_type];
    if (label) {
      const score = p.ai_score || 0;
      results.push({
        label,
        status: score >= 7 ? "exact" : score >= 4 ? "close" : "miss",
        detail: p.ai_score != null ? "AI: " + p.ai_score + "/10" : undefined,
      });
    }
  }

  return results.slice(0, 6);
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

const SOURCE_TAG: Record<string, string> = {
  "Clive Emson Auctions": "auction",
  "Allsop Auctions": "auction",
  "SDL Auctions": "auction",
  "UK Auction List": "auction",
  "Heritage at Risk Register": "heritage",
  "Charities Commission (Pre-Market Signal)": "signal",
  "Planning Portal (Pre-Market Signal)": "signal",
  "Church of England": "church",
  "Church of Scotland": "church",
  "Church in Wales": "church",
  "Methodist Church": "church",
  "Baptist Union": "church",
  "Diocese of London": "church",
};

export default function PropertyCard({ property: p, matchScore, criteria = [], isFaved = false }: Props) {
  const navigate = useNavigate();
  const qc       = useQueryClient();
  const [faved,  setFaved]  = useState(isFaved);
  const [modal,  setModal]  = useState(false);
  const [sent,   setSent]   = useState(false);
  const [imgErr, setImgErr] = useState(false);

  const favMut = useMutation({
    mutationFn: () => faved ? favouritesApi.remove(p.id) : favouritesApi.add(p.id),
    onSuccess: () => {
      setFaved(f => !f);
      qc.invalidateQueries({ queryKey: ["favourites"] });
    },
  });

  const ms     = matchScore ?? 100;
  const msStr  = ms >= 95 ? "100" : ms >= 85 ? "90" : ms >= 75 ? "80" : ms >= 65 ? "70" : ms >= 50 ? "60" : "30";
  const imgUrl = p.image_url || (p.images && p.images[0]) || null;

  if (p.is_off_market) {
    return (
      <div className="pcard off-market">
        <div className="pcard-img">
          <div className="pcard-img-placeholder">&#9962;</div>
        </div>
        <div className="pcard-body">
          <div className="pcard-title">{p.title}</div>
          <div className="pcard-meta">
            <span>{p.location}</span>
            <span>{p.price_raw || "POA"}</span>
          </div>
        </div>
        <div className="pcard-match" data-score={msStr}>
          <span className="pcard-match__pct">{ms}%</span>
          <span className="pcard-match__label">match</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="pcard">

        <div className="pcard-img">
          {(imgUrl && !imgErr)
            ? <img src={imgUrl} alt={p.title} onError={() => setImgErr(true)} loading="lazy" />
            : <div className="pcard-img-placeholder">&#9962;</div>
          }
          <span className="pcard-source-badge">{p.source}</span>
        </div>

        <button
          className={"pcard-fav" + (faved ? " saved" : "")}
          onClick={e => { e.stopPropagation(); favMut.mutate(); }}
          title={faved ? "Remove from saved" : "Save property"}
        >
          <Heart size={13} fill={faved ? "#d4170f" : "none"} color={faved ? "#d4170f" : "var(--mid)"} />
        </button>

        <div className="pcard-body">
          <div>
            <div className="pcard-top">
              <span
                className="pcard-title"
                onClick={() => navigate("/properties/" + p.id)}
              >
                {p.title}
              </span>
              <span className="pcard-price">{p.price_raw || "POA"}</span>
            </div>

            <div className="pcard-meta">
              <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <MapPin size={10} />
                {p.location}
              </span>
              {p.listing_type === "auction" && (
                <span style={{ color: "var(--orange)" }}>Auction</span>
              )}
              {p.is_listed && (
                <span>Grade {p.listed_grade} listed</span>
              )}
              <span style={{ marginLeft: "auto" }}>
                {formatDistanceToNow(new Date(p.first_seen), { addSuffix: true })}
              </span>
            </div>

            {criteria.length > 0 && (
              <div className="pcard-criteria">
                {criteria.map((c, i) => (
                  <span key={i} className={"criterion " + c.status}>
                    {c.status === "exact" ? "✓" : c.status === "close" ? "~" : "✗"}
                    {" "}{c.label}
                    {c.detail ? " · " + c.detail : ""}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="pcard-actions">
            <button
              className="pcard-btn primary"
              onClick={() => navigate("/properties/" + p.id)}
            >
              View more
            </button>
            {sent ? (
              <span style={{ fontSize: "0.72rem", color: "var(--green)" }}>
                ✓ Sent
              </span>
            ) : (
              <button className="pcard-btn" onClick={() => setModal(true)}>
                <Mail size={11} /> Contact
              </button>
            )}
            <button
              className="pcard-btn"
              onClick={e => { e.stopPropagation(); window.open(p.source_url, "_blank", "noopener,noreferrer"); }}
            >
              <ExternalLink size={11} /> Source
            </button>
          </div>
        </div>

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
