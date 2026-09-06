import { useSEO } from "../hooks/useSEO";
import { useNavigate } from "react-router-dom";
import { useSearchStore } from "../stores/searchStore";
import { useState } from "react";
import { Search } from "lucide-react";

const REGIONS = [
  { name: "London",         slug:"london",         count: 18, radius: 45, blurb: "Over 2,000 listed church buildings; Victorian churches in Hackney, Croydon and Greenwich come to market regularly." },
  { name: "Yorkshire",      slug:"yorkshire",      count: 24, radius: 35, blurb: "One of England's highest concentrations of Methodist chapels — stone-built in Barnsley, Halifax and Huddersfield." },
  { name: "Wales",          slug:"wales",          count: 22, radius: 50, blurb: "Extraordinary density of Nonconformist chapels; beautiful stone buildings in the valleys at competitive prices." },
  { name: "The Midlands",   slug:"the-midlands",   count: 19, radius: 40, blurb: "Thousands of 19th-century nonconformist chapels from its industrial heritage, now available for new uses." },
  { name: "Lancashire",     slug:"lancashire",     count: 15, radius: 30, blurb: "Victorian Gothic Revival churches across the mill towns — Burnley, Nelson and Accrington." },
  { name: "Manchester",     slug:"manchester",     count: 13, radius: 25, blurb: "Hundreds of churches from rapid Victorian expansion; Grade II listed examples in Ancoats and Hulme." },
  { name: "Kent",           slug:"kent",           count: 11, radius: 30, blurb: "The Garden of England — medieval parish churches and redundant rural churches near Canterbury and Maidstone." },
  { name: "Scotland",       slug:"scotland",       count: 9,  radius: 60, blurb: "Distinctive Presbyterian kirks alongside Victorian Gothic, many Category A or B listed." },
  { name: "Devon",          slug:"devon",          count: 8,  radius: 40, blurb: "Ancient parish churches from Norman times; Methodist chapels in fishing villages and market towns." },
  { name: "Surrey",         slug:"surrey",         count: 7,  radius: 25, blurb: "Prosperous commuter belt with Victorian and Edwardian church buildings ripe for conversion." },
  { name: "Essex",          slug:"essex",          count: 6,  radius: 30, blurb: "Historic market towns and coastal communities with redundant churches ripe for conversion." },
  { name: "Sussex",         slug:"sussex",         count: 5,  radius: 30, blurb: "Coastal and rural churches from Brighton to Chichester, many Grade II listed." },
  { name: "Hampshire",      slug:"hampshire",      count: 5,  radius: 35, blurb: "Cathedral city of Winchester plus coastal towns and rural parishes." },
  { name: "Dorset",         slug:"dorset",         count: 4,  radius: 30, blurb: "Hardy country — quiet market town chapels and rural parish churches along the coast." },
  { name: "Somerset",       slug:"somerset",       count: 4,  radius: 35, blurb: "Bath, Wells and the Levels — historic ecclesiastical buildings at accessible prices." },
  { name: "Cornwall",       slug:"cornwall",       count: 4,  radius: 40, blurb: "Methodist stronghold — hundreds of stone chapels in fishing villages and market towns." },
  { name: "Norfolk",        slug:"norfolk",        count: 3,  radius: 35, blurb: "More medieval churches per square mile than anywhere else in Europe." },
  { name: "Suffolk",        slug:"suffolk",        count: 3,  radius: 30, blurb: "Wool churches and market town chapels from Ipswich to Bury St Edmunds." },
  { name: "Oxfordshire",    slug:"oxfordshire",    count: 3,  radius: 25, blurb: "University city spires and market town chapels within easy reach of London." },
  { name: "Shropshire",     slug:"shropshire",     count: 2,  radius: 30, blurb: "Rural border county with stone chapels and redundant parish churches." },
  { name: "Cumbria",        slug:"cumbria",        count: 2,  radius: 45, blurb: "Lake District villages and market towns — dramatic settings for conversion projects." },
  { name: "Northumberland", slug:"northumberland", count: 2,  radius: 45, blurb: "Border country with ancient churches and remote rural chapels." },
  { name: "Lincolnshire",   slug:"lincolnshire",   count: 2,  radius: 35, blurb: "Flat fenlands with tall-spired market town churches and Nonconformist chapels." },
  { name: "Derbyshire",     slug:"derbyshire",     count: 2,  radius: 30, blurb: "Peak District villages and market town chapels — popular for conversion." },
];

const totalProps = REGIONS.reduce((a, r) => a + r.count, 0);

export default function LocationPage() {
  useSEO({
    title: "Churches for Sale by Region — Ulouka",
    description: "Browse churches, chapels and places of worship for sale across every region of the UK.",
  });

  const navigate = useNavigate();
  const { setQuery } = useSearchStore();
  const [searchVal, setSearchVal] = useState("");

  function handleRegionClick(region: typeof REGIONS[0]) {
    setQuery(`churches for sale in ${region.name}`);
    navigate(`/results?region=${region.slug}`);
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = searchVal.trim();
    if (!trimmed) return;
    setQuery(trimmed);
    navigate("/results");
  }

  const filtered = searchVal.trim()
    ? REGIONS.filter(r => r.name.toLowerCase().includes(searchVal.toLowerCase()))
    : REGIONS;

  return (
    <main style={{ maxWidth:1040, margin:"0 auto", padding:"80px 22px 90px", animation:"riseIn .6s cubic-bezier(.16,1,.3,1) both" }}>

      {/* ── Header row: title left, search right on desktop ── */}
      <div style={{ display:"flex", alignItems:"flex-end", justifyContent:"space-between", flexWrap:"wrap", gap:20, marginBottom:18 }}>
        <section style={{ maxWidth:580 }}>
          <p style={{ font:"500 12px 'Space Grotesk'", letterSpacing:"0.16em", textTransform:"uppercase", color:"var(--ink3)", margin:"0 0 18px" }}>Browse by region</p>
          <h1 style={{ fontFamily:"'Gabarito'", fontWeight:900, fontSize:"clamp(38px,5.6vw,60px)", lineHeight:1.0, letterSpacing:"-0.04em", color:"var(--ink)", margin:0 }}>
            Every corner of the UK,{" "}
            <em style={{ fontFamily:"'League Script', cursive", fontStyle:"normal", fontWeight:400, WebkitTextStroke:"0.7px #6b70c2", color:"#6b70c2", fontSize:"0.72em", verticalAlign:"0.02em" }}>in one place</em>
          </h1>
          <p style={{ font:"300 18px/1.55 'Space Grotesk'", color:"var(--ink2)", margin:"16px 0 0", maxWidth:520 }}>
            Choose a region to see churches, chapels and places of worship currently on the market.
          </p>
        </section>

        {/* Search bar — left-aligned on desktop, full-width on mobile */}
        <form onSubmit={handleSearch} style={{ display:"flex", alignItems:"center", gap:8, background:"var(--surface)", border:"1px solid var(--line)", borderRadius:14, padding:"8px 8px 8px 16px", boxShadow:"0 2px 12px rgba(0,0,0,0.05)", minWidth:280, maxWidth:340, width:"100%" }}>
          <Search size={15} style={{ color:"var(--ink3)", flexShrink:0 }} />
          <input
            value={searchVal}
            onChange={e => setSearchVal(e.target.value)}
            placeholder="Search any region, town or county…"
            style={{ flex:1, border:"none", outline:"none", background:"transparent", font:"400 14px 'Space Grotesk'", color:"var(--ink)", minWidth:0 }}
          />
          {searchVal && (
            <button type="submit" style={{ flexShrink:0, background:"var(--btnbg)", color:"var(--btnfg)", border:"none", borderRadius:8, padding:"6px 12px", font:"500 13px 'Space Grotesk'", cursor:"pointer" }}>
              Go
            </button>
          )}
        </form>
      </div>

      {/* Stats strip */}
      <div style={{ display:"flex", gap:40, padding:"22px 0 26px", margin:"24px 0 8px", borderTop:"1px solid var(--line)", borderBottom:"1px solid var(--line)" }}>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>{totalProps}</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>live listings</p>
        </div>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>{REGIONS.length}</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>regions covered</p>
        </div>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>30+</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>sources</p>
        </div>
      </div>

      {/* Region grid */}
      {filtered.length === 0 ? (
        <div style={{ textAlign:"center", padding:"60px 0", color:"var(--ink3)" }}>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:700, fontSize:18, marginBottom:8, color:"var(--ink)" }}>No regions found</p>
          <p style={{ font:"300 15px 'Space Grotesk'" }}>Try searching the whole UK instead.</p>
          <button onClick={() => { setQuery(searchVal); navigate("/results"); }}
            style={{ marginTop:16, background:"var(--btnbg)", color:"var(--btnfg)", border:"none", borderRadius:980, padding:"10px 22px", font:"500 14px 'Space Grotesk'", cursor:"pointer" }}>
            Search "{searchVal}" across all UK
          </button>
        </div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:16, marginTop:28 }}>
          {filtered.map(r => (
            <button
              key={r.name}
              onClick={() => handleRegionClick(r)}
              style={{ textDecoration:"none", display:"block", background:"var(--surface)", border:"1px solid var(--line)", borderRadius:22, padding:"22px 22px 20px", cursor:"pointer", boxShadow:"0 1px 3px rgba(0,0,0,0.04)", transition:"all .28s cubic-bezier(.16,1,.3,1)", textAlign:"left", width:"100%", fontFamily:"inherit" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform="translateY(-4px)"; (e.currentTarget as HTMLElement).style.boxShadow="0 18px 46px rgba(0,0,0,0.1)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform="none"; (e.currentTarget as HTMLElement).style.boxShadow="0 1px 3px rgba(0,0,0,0.04)"; }}
            >
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
                <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                  <span style={{ display:"inline-flex", alignItems:"center", gap:6, background:"var(--surface2)", borderRadius:980, padding:"4px 10px", font:"500 11px 'Space Grotesk'", color:"var(--ink2)" }}>
                    <span style={{ width:5, height:5, borderRadius:"50%", background:"#6b70c2", display:"inline-block" }} />
                    {r.count} listings
                  </span>
                  <span style={{ font:"400 11px 'Space Grotesk'", color:"var(--ink3)", background:"var(--surface2)", borderRadius:980, padding:"4px 10px" }}>
                    ~{r.radius}mi radius
                  </span>
                </div>
                <span style={{ fontSize:16, color:"var(--ink3)", lineHeight:1 }}>→</span>
              </div>
              <h3 style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:21, letterSpacing:"-0.02em", color:"var(--ink)", margin:"0 0 7px" }}>{r.name}</h3>
              <p style={{ font:"300 13px/1.6 'Space Grotesk'", color:"var(--ink2)", margin:0 }}>{r.blurb}</p>
            </button>
          ))}
        </div>
      )}

      {/* Mobile search bar CSS override via inline style tag */}
      <style>{`
        @media (max-width: 600px) {
          form[data-region-search] {
            max-width: 100% !important;
            justify-content: center !important;
          }
        }
      `}</style>
    </main>
  );
}