import { useSEO } from "../hooks/useSEO";
import { useNavigate } from "react-router-dom";
import { useSearchStore } from "../stores/searchStore";

const REGIONS = [
  { name: "London",       slug:"london",       count: 18, blurb: "Over 2,000 listed church buildings; Victorian churches in Hackney, Croydon and Greenwich come to market regularly." },
  { name: "Yorkshire",    slug:"yorkshire",    count: 24, blurb: "One of England's highest concentrations of Methodist chapels — stone-built in Barnsley, Halifax and Huddersfield." },
  { name: "Wales",        slug:"wales",        count: 22, blurb: "Extraordinary density of Nonconformist chapels; beautiful stone buildings in the valleys at competitive prices." },
  { name: "The Midlands", slug:"the-midlands", count: 19, blurb: "Thousands of 19th-century nonconformist chapels from its industrial heritage, now available for new uses." },
  { name: "Lancashire",   slug:"lancashire",   count: 15, blurb: "Victorian Gothic Revival churches across the mill towns — Burnley, Nelson and Accrington." },
  { name: "Manchester",   slug:"manchester",   count: 13, blurb: "Hundreds of churches from rapid Victorian expansion; Grade II listed examples in Ancoats and Hulme." },
  { name: "Kent",         slug:"kent",         count: 11, blurb: "The Garden of England — medieval parish churches and redundant rural churches near Canterbury and Maidstone." },
  { name: "Scotland",     slug:"scotland",     count: 9,  blurb: "Distinctive Presbyterian kirks alongside Victorian Gothic, many Category A or B listed." },
  { name: "Devon",        slug:"devon",        count: 8,  blurb: "Ancient parish churches from Norman times; Methodist chapels in fishing villages and market towns." },
  { name: "Surrey",       slug:"surrey",       count: 7,  blurb: "Prosperous commuter belt with Victorian and Edwardian church buildings ripe for conversion." },
];

const totalProps = REGIONS.reduce((a, r) => a + r.count, 0);

export default function LocationPage() {
  useSEO({
    title: "Churches for Sale by Region — Nave",
    description: "Browse churches, chapels and places of worship for sale across every region of the UK.",
  });

  const navigate = useNavigate();
  const { setQuery } = useSearchStore();

  function handleRegionClick(region: typeof REGIONS[0]) {
    setQuery(`churches for sale in ${region.name}`);
    navigate(`/results?region=${region.slug}`);
  }

  return (
    <main style={{ maxWidth:1040, margin:"0 auto", padding:"80px 22px 90px", animation:"riseIn .6s cubic-bezier(.16,1,.3,1) both" }}>

      <section style={{ maxWidth:680, marginBottom:18 }}>
        <p style={{ font:"500 12px 'Space Grotesk'", letterSpacing:"0.16em", textTransform:"uppercase", color:"var(--ink3)", margin:"0 0 18px" }}>Browse by region</p>
        <h1 style={{ fontFamily:"'Gabarito'", fontWeight:900, fontSize:"clamp(38px,5.6vw,60px)", lineHeight:1.0, letterSpacing:"-0.04em", color:"var(--ink)", margin:0 }}>
          Every corner of the UK,{" "}
          <em style={{ fontFamily:"'League Script', cursive", fontStyle:"normal", fontWeight:400, WebkitTextStroke:"0.7px #6b70c2", color:"#6b70c2", fontSize:"0.72em", verticalAlign:"0.02em" }}>in one place</em>
        </h1>
        <p style={{ font:"300 20px/1.55 'Space Grotesk'", color:"var(--ink2)", margin:"24px 0 0", maxWidth:560 }}>
          Choose a region to see churches, chapels and places of worship currently on the market — aggregated from 30+ sources.
        </p>
      </section>

      {/* Stats strip */}
      <div style={{ display:"flex", gap:40, padding:"26px 0 30px", margin:"34px 0 8px", borderTop:"1px solid var(--line)", borderBottom:"1px solid var(--line)" }}>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>{totalProps}</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>live listings</p>
        </div>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>10</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>regions covered</p>
        </div>
        <div>
          <p style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:30, color:"var(--ink)", margin:0, letterSpacing:"-0.02em" }}>30+</p>
          <p style={{ font:"400 13px 'Space Grotesk'", color:"var(--ink3)", margin:"4px 0 0" }}>sources, updated every 3h</p>
        </div>
      </div>

      {/* Region grid */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(300px,1fr))", gap:20, marginTop:34 }}>
        {REGIONS.map(r => (
          <button
            key={r.name}
            onClick={() => handleRegionClick(r)}
            style={{ textDecoration:"none", display:"block", background:"var(--surface)", border:"1px solid var(--line)", borderRadius:22, padding:"24px 24px 22px", cursor:"pointer", boxShadow:"0 1px 3px rgba(0,0,0,0.04)", transition:"all .28s cubic-bezier(.16,1,.3,1)", textAlign:"left", width:"100%", fontFamily:"inherit" }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform="translateY(-4px)"; (e.currentTarget as HTMLElement).style.boxShadow="0 18px 46px rgba(0,0,0,0.1)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform="none"; (e.currentTarget as HTMLElement).style.boxShadow="0 1px 3px rgba(0,0,0,0.04)"; }}
          >
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
              <span style={{ display:"inline-flex", alignItems:"center", gap:7, background:"var(--surface2)", borderRadius:980, padding:"5px 12px", font:"500 12px 'Space Grotesk'", color:"var(--ink2)" }}>
                <span style={{ width:6, height:6, borderRadius:"50%", background:"#6b70c2", display:"inline-block" }} />
                {r.count} listings
              </span>
              <span style={{ fontSize:18, color:"var(--ink3)", lineHeight:1 }}>→</span>
            </div>
            <h3 style={{ fontFamily:"'Gabarito'", fontWeight:800, fontSize:23, letterSpacing:"-0.02em", color:"var(--ink)", margin:"0 0 8px" }}>{r.name}</h3>
            <p style={{ font:"300 14px/1.6 'Space Grotesk'", color:"var(--ink2)", margin:0 }}>{r.blurb}</p>
          </button>
        ))}
      </div>
    </main>
  );
}