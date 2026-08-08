import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, ExternalLink, Mail, MapPin, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { favouritesApi } from "../../api/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import InterestModal from "../ui/InterestModal";
import { useAuthStore } from "../../stores/authStore";
import { descriptionSnippet } from "../../utils/text";

interface Props {
  property:    any;
  matchScore?: number;
  criteria?:   any[];
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
  if (intent.price_max) {
    const m = (property.price_raw || property.price || "").match(/£([\d,]+)/);
    const v = m ? parseInt(m[1].replace(/,/g, "")) : null;
    if (v && v <= intent.price_max)
      results.push({ label: `Under £${(intent.price_max/1000).toFixed(0)}k`, status: "exact", detail: property.price_raw });
    else if (v && v <= intent.price_max * 1.15)
      results.push({ label: `Near £${(intent.price_max/1000).toFixed(0)}k`, status: "close", detail: property.price_raw });
    else if (v)
      results.push({ label: `Over £${(intent.price_max/1000).toFixed(0)}k`, status: "miss", detail: property.price_raw });
  }
  if (intent.locations?.length) {
    const loc = (property.location || "").toLowerCase();
    results.push({ label: intent.locations[0], status: intent.locations.some((l: string) => loc.includes(l.toLowerCase())) ? "exact" : "miss" });
  }
  for (const feat of (intent.features || [])) {
    const field = ({ parking:"has_parking", graveyard:"has_graveyard", hall:"has_hall", spire:"has_spire" } as any)[feat];
    results.push({ label: feat.charAt(0).toUpperCase()+feat.slice(1), status: (field && property[field]) ? "exact" : "miss" });
  }
  return results.slice(0, 5);
}

export function computeMatchScore(criteria: CriterionResult[]): number {
  if (!criteria.length) return 100;
  const exact = criteria.filter(c => c.status === "exact").length;
  const close = criteria.filter(c => c.status === "close").length;
  const raw = Math.round(((exact + close * 0.6) / criteria.length) * 100);
  if (raw >= 95) return 100; if (raw >= 85) return 90; if (raw >= 75) return 80;
  if (raw >= 65) return 70; if (raw >= 50) return 60; return 30;
}

function toTitleCase(str: string): string {
  if (!str) return "";
  if (str === str.toUpperCase() && str.length > 4)
    return str.split(" ").map(w => w.length > 3 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase()).join(" ");
  return str;
}

function cleanTitle(raw: string, location: string): string {
  if (!raw) return "Church Property";
  // If title is very long it's likely a description — extract first sentence or truncate
  if (raw.length > 80) {
    // Try to get first sentence
    const firstSentence = raw.split(/[.!?]/)[0].trim();
    if (firstSentence.length >= 10 && firstSentence.length <= 80) return toTitleCase(firstSentence);
    // Otherwise take first 7 words
    const words = raw.split(" ").slice(0, 7).join(" ").replace(/[,;:]$/, "");
    return toTitleCase(words);
  }
  return toTitleCase(raw);
}

const SOURCE_TAG_TYPE: Record<string, string> = {
  "Clive Emson Auctions":"auction","Allsop Auctions":"auction",
  "SDL Auctions":"auction","UK Auction List":"auction","EIG Property Auctions":"auction",
  "Alex Martin Commercial":"specialist",
  "Church of England":"church","Church of Scotland":"church","Church in Wales":"church",
  "Methodist Church":"church","Diocese of London":"church","Church Growth Trust":"church",
  "Churches Conservation Trust":"heritage",
  "Charities Commission":"signal","Companies House":"signal","Planning Portal":"signal","GOV.UK":"signal",
  "OnTheMarket":"portal","Jitty":"portal","OpenRent":"portal",
};

const TYPE_EMOJI: Record<string, string> = { church:"⛪", hall:"🏛", large_space:"🏢", other:"🏠" };

const BAD_URLS = ["facebook","twitter","instagram","gravatar","avatar","logo","icon","badge",
  "placeholder","animal","dog","cat","bird","butterfly","unsplash","pexels",
  "shutterstock","gettyimages","istockphoto","data:image","maps.google","gstatic"];

function ImageSlideshow({ images, emoji, title }: { images: string[]; emoji: string; title: string }) {
  const [idx, setIdx] = useState(0);
  const [failed, setFailed] = useState<Set<number>>(new Set());

  const valid = images.filter((_, i) => !failed.has(i));
  const cur = idx % Math.max(valid.length, 1);

  const handleError = () => {
    const originalIdx = images.indexOf(valid[cur]);
    setFailed(prev => new Set(prev).add(originalIdx));
  };

  if (valid.length === 0) return (
    <div className="pcard-img-placeholder skeleton" style={{ minHeight:"inherit" }} />
  );

  const prev = (e: React.MouseEvent) => { e.stopPropagation(); setIdx(i => (i - 1 + valid.length) % valid.length); };
  const next = (e: React.MouseEvent) => { e.stopPropagation(); setIdx(i => (i + 1) % valid.length); };

  return (
    <>
      <img key={valid[cur]} src={valid[cur]} alt={title} onError={handleError} loading="lazy"
        style={{ width:"100%", height:"100%", objectFit:"cover", display:"block" }} />
      {valid.length > 1 && (
        <>
          <button onClick={prev} style={{ position:"absolute", left:4, top:"50%", transform:"translateY(-50%)",
            background:"rgba(0,0,0,.5)", color:"#fff", border:"none", borderRadius:"50%",
            width:22, height:22, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <ChevronLeft size={13}/>
          </button>
          <button onClick={next} style={{ position:"absolute", right:4, top:"50%", transform:"translateY(-50%)",
            background:"rgba(0,0,0,.5)", color:"#fff", border:"none", borderRadius:"50%",
            width:22, height:22, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <ChevronRight size={13}/>
          </button>
          <div style={{ position:"absolute", bottom:5, left:"50%", transform:"translateX(-50%)", display:"flex", gap:3 }}>
            {valid.map((_: string, i: number) => (
              <span key={i} onClick={e => { e.stopPropagation(); setIdx(i); }} style={{
                width:5, height:5, borderRadius:"50%", cursor:"pointer", display:"inline-block",
                background: i === cur ? "#fff" : "rgba(255,255,255,.4)" }}/>
            ))}
          </div>
        </>
      )}
    </>
  );
}

export default function PropertyCard({ property: p, matchScore, criteria = [], isFaved = false }: Props) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [faved, setFaved] = useState(isFaved);
  const [modal, setModal] = useState(false);
  const [sent, setSent] = useState(false);

  const { isLoggedIn, openGate } = useAuthStore();
  const favMut = useMutation({
    mutationFn: () => faved ? favouritesApi.remove(p.id) : favouritesApi.add(p.id),
    onSuccess: () => { setFaved(f => !f); qc.invalidateQueries({ queryKey: ["favourites"] }); },
  });

  const ms = matchScore ?? p._score ?? 100;
  const msStr = ms >= 95 ? "100" : ms >= 85 ? "90" : ms >= 75 ? "80" : ms >= 65 ? "70" : ms >= 50 ? "60" : "30";
  const criteria_ = criteria.length > 0 ? criteria : (p._criteria || []);
  const emoji = TYPE_EMOJI[p.property_type || "other"] || "⛪";
  const tagType = SOURCE_TAG_TYPE[p.source] || "portal";
  const rawTitle = (p.title || "").replace(/£[\d,]+(\s*[-–]\s*£[\d,]+)?/g, "").replace(/\s{2,}/g, " ").trim();
  const title = cleanTitle(rawTitle, p.location || "");
  const location = (p.location || "Location unknown");
  const priceRaw = (p.price_raw || p.price || "POA").replace(/([^\s])£/, "$1 £").trim();
  const isPOA = ["POA","Enquire","TBC","See article","Heritage at Risk","Filing signal","Planning stage"].some(x => priceRaw.includes(x));
  const snippet = descriptionSnippet(p.description, 120);
  const timeAgo = p.first_seen ? formatDistanceToNow(new Date(p.first_seen), { addSuffix: true }) : "";

  const rawImgs: string[] = Array.isArray(p.images) && p.images.length > 0 ? p.images : p.image_url ? [p.image_url] : [];
  const imgs: string[] = rawImgs.filter((u: string) =>
    typeof u === "string" && u.startsWith("http") && !BAD_URLS.some(b => u.toLowerCase().includes(b))
  );

  return (
    <div>
      <div className="pcard">
        <div className="pcard-img" style={{ position:"relative" }}>
          <ImageSlideshow images={imgs} emoji={emoji} title={title} />
        </div>

        <button className={"pcard-fav" + (faved ? " saved" : "")}
          onClick={e => { e.stopPropagation(); if (!isLoggedIn) { openGate("favourite"); return; } favMut.mutate(); }}
          title={faved ? "Remove" : "Save"}>
          <Heart size={12} fill={faved ? "#d4170f" : "none"} color={faved ? "#d4170f" : "var(--mid)"} />
        </button>

        <div className="pcard-body">
          <div>
            <div style={{ marginBottom:6 }}>
              <span className={`tag ${tagType}`}>{p.source}</span>
              {p.listing_type === "auction" && <span className="tag auction" style={{ marginLeft:4 }}>Auction</span>}
            </div>
            <div className="pcard-title" onClick={() => navigate("/properties/" + p.id)}>{title}</div>
            <div className="pcard-meta">
              <span style={{ display:"flex", alignItems:"center", gap:3 }}>
                <MapPin size={10}/>{location}
              </span>
              {isPOA
                ? <span style={{ fontStyle:"italic" }}>{priceRaw}</span>
                : <strong style={{ color:"var(--ink)", fontSize:"0.8rem" }}>{priceRaw}</strong>
              }
              <span style={{ display:"flex", alignItems:"center", gap:3, marginLeft:"auto" }}>
                <Clock size={9}/>{timeAgo}
              </span>
            </div>
            {criteria_.length > 0 && (
              <div className="pcard-criteria">
                {criteria_.map((c: any, i: number) => (
                  <span key={i} className={"criterion " + c.status}>
                    {c.status === "exact" ? "✓" : c.status === "close" ? "~" : "✗"} {c.label}
                    {c.detail ? " · " + c.detail : ""}
                  </span>
                ))}
              </div>
            )}
            {snippet && <p className="pcard-desc">{snippet}</p>}
          </div>

          <div className="pcard-actions">
            <button className="pcard-btn primary" onClick={() => navigate("/properties/" + p.id)}>View more</button>
            {sent
              ? <span style={{ fontSize:"0.7rem", color:"var(--green)" }}>✓ Sent</span>
              : <button className="pcard-btn" onClick={() => { if (!isLoggedIn) { openGate("enquiry"); return; } setModal(true); }}><Mail size={10}/> Contact</button>
            }
            <button className="pcard-btn" onClick={e => {
              e.stopPropagation();
              (window as any).umami?.track("source-click", { source: p.source });
              window.open(p.source_url || p.url, "_blank", "noopener,noreferrer");
            }}>
              <ExternalLink size={10}/> Source
            </button>
          </div>
        </div>

        <div className="pcard-match" data-score={msStr} onClick={() => navigate("/properties/" + p.id)}>
          <span className="pcard-match__pct">{ms}%</span>
          <span className="pcard-match__label">match</span>
        </div>
      </div>
      {modal && <InterestModal property={p} onClose={() => setModal(false)} onSent={() => { setSent(true); setModal(false); }} />}
    </div>
  );
}