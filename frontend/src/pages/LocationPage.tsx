/**
 * LocationPage — /churches-for-sale/:region
 *
 * SEO-optimised landing page for each UK region.
 * Shows filtered listings with descriptive content for Google ranking.
 * Each page targets: "churches for sale in [region]" keywords.
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSEO } from "../hooks/useSEO";
import { api } from "../api/client";
import PropertyCard from "../components/property/PropertyCard";
import SkeletonCards from "../components/ui/SkeletonCards";

const REGION_META: Record<string, {
  name:        string;
  description: string;
  facts:       string;
}> = {
  london: {
    name: "London",
    description: "Churches and chapels for sale in London and Greater London, including inner city ecclesiastical buildings, places of worship, and former churches available for conversion or community use.",
    facts: "London has over 2,000 listed church buildings. Many former Victorian churches in areas like Hackney, Croydon, and Greenwich are now available for community or residential conversion.",
  },
  yorkshire: {
    name: "Yorkshire",
    description: "Churches, chapels, and places of worship for sale across Yorkshire including West Yorkshire, South Yorkshire, North Yorkshire, and East Yorkshire.",
    facts: "Yorkshire has one of the highest concentrations of Methodist chapels in England, many of which became redundant as congregations declined. Stone-built chapels in areas like Barnsley, Halifax, and Huddersfield regularly come to market.",
  },
  kent: {
    name: "Kent",
    description: "Churches and chapels for sale in Kent, the Garden of England, including properties near Canterbury, Maidstone, and the Kent coast.",
    facts: "Kent is home to Canterbury Cathedral and hundreds of medieval parish churches. Redundant rural churches in villages across the county offer unique conversion opportunities.",
  },
  surrey: {
    name: "Surrey",
    description: "Churches and places of worship for sale in Surrey, including properties in Guildford, Woking, and the Surrey Hills.",
    facts: "Surrey's prosperous commuter belt contains numerous Victorian and Edwardian church buildings, many of which are available as residential conversions or community spaces.",
  },
  midlands: {
    name: "The Midlands",
    description: "Churches and chapels for sale across the Midlands including Birmingham, Coventry, Leicester, Nottingham, and surrounding counties.",
    facts: "The Midlands industrial heritage produced thousands of nonconformist chapels during the 19th century. Many of these substantial brick buildings are now available for new uses.",
  },
  manchester: {
    name: "Manchester",
    description: "Churches and places of worship for sale in Manchester and Greater Manchester including Salford, Stockport, and surrounding areas.",
    facts: "Manchester's rapid Victorian expansion created hundreds of churches and chapels across the city. Many Grade II listed examples in areas like Ancoats and Hulme are available for sympathetic conversion.",
  },
  wales: {
    name: "Wales",
    description: "Churches and chapels for sale across Wales including Cardiff, Swansea, and rural Welsh communities.",
    facts: "Wales has an extraordinary density of Nonconformist chapels per head of population. Many beautiful stone chapels in the Welsh valleys and rural areas are available at very competitive prices.",
  },
  scotland: {
    name: "Scotland",
    description: "Churches and places of worship for sale across Scotland including Edinburgh, Glasgow, and the Scottish Highlands.",
    facts: "Scotland's church buildings reflect its unique religious history, with distinctive Presbyterian kirks alongside Victorian Gothic churches. Many are Category A or B listed buildings.",
  },
  devon: {
    name: "Devon",
    description: "Churches and chapels for sale in Devon including Exeter, Plymouth, and rural Devon villages.",
    facts: "Devon has hundreds of ancient parish churches, many dating from Norman times. Methodist chapels in fishing villages and market towns are particularly sought after for conversion.",
  },
  lancashire: {
    name: "Lancashire",
    description: "Churches and chapels for sale in Lancashire including Blackpool, Preston, Burnley, and the Ribble Valley.",
    facts: "Lancashire's textile mill towns produced a remarkable collection of Victorian churches and chapels. Many substantial Gothic Revival buildings are available in towns like Burnley, Nelson, and Accrington.",
  },
};

export default function LocationPage() {
  const { region }  = useParams<{ region: string }>();
  const navigate    = useNavigate();
  const [listings, setListings] = useState<any[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [total,    setTotal]    = useState(0);

  const meta = REGION_META[region || ""] || {
    name:        region ? region.charAt(0).toUpperCase() + region.slice(1) : "UK",
    description: `Churches and chapels for sale in ${region}.`,
    facts:       "",
  };

  useSEO({
    title:       `Churches for Sale in ${meta.name}`,
    description: meta.description,
  });

  useEffect(() => {
    if (!region) return;
    setLoading(true);
    api.post("/api/search", {
      query:   `church in ${region}`,
      filters: {},
      page:    1,
      per_page: 20,
    }).then(r => {
      setListings(r.data.results || []);
      setTotal(r.data.total || 0);
    }).finally(() => setLoading(false));
  }, [region]);

  return (
    <main className="wrap" style={{ paddingTop: 40, paddingBottom: 80 }}>

      {/* Hero */}
      <div style={{ marginBottom: 40 }}>
        <p style={{ fontSize:"0.75rem", color:"var(--mid)", marginBottom:8,
                    letterSpacing:".08em", textTransform:"uppercase" }}>
          Churches for sale
        </p>
        <h1 style={{ fontSize:"clamp(1.6rem,4vw,2.4rem)", fontWeight:800,
                     lineHeight:1.15, marginBottom:16 }}>
          {meta.name}
        </h1>
        <p style={{ fontSize:"0.92rem", color:"var(--ink-soft)", lineHeight:1.7,
                    maxWidth:640, marginBottom:0 }}>
          {meta.description}
        </p>
      </div>

      {/* Stats bar */}
      <div style={{
        display:"flex", gap:24, marginBottom:32,
        padding:"12px 0", borderTop:"1px solid var(--rule)",
        borderBottom:"1px solid var(--rule)",
      }}>
        <div>
          <p style={{ fontSize:"1.4rem", fontWeight:800, margin:0 }}>{total}</p>
          <p style={{ fontSize:"0.72rem", color:"var(--mid)", margin:0 }}>
            {total === 1 ? "property" : "properties"} listed
          </p>
        </div>
        <div>
          <p style={{ fontSize:"1.4rem", fontWeight:800, margin:0 }}>30+</p>
          <p style={{ fontSize:"0.72rem", color:"var(--mid)", margin:0 }}>sources</p>
        </div>
        <div>
          <p style={{ fontSize:"1.4rem", fontWeight:800, margin:0 }}>Free</p>
          <p style={{ fontSize:"0.72rem", color:"var(--mid)", margin:0 }}>to search</p>
        </div>
      </div>

      {/* Listings */}
      {loading ? (
        <SkeletonCards count={6} />
      ) : listings.length === 0 ? (
        <div style={{ textAlign:"center", padding:"60px 0", color:"var(--mid)" }}>
          <p style={{ fontSize:"1rem", marginBottom:12 }}>
            No listings found in {meta.name} right now.
          </p>
          <button className="btn btn-black" onClick={() => navigate("/")}>
            Search all UK properties
          </button>
        </div>
      ) : (
        <div className="results-grid">
          {listings.map(l => (
            <PropertyCard key={l.id} property={l} />
          ))}
        </div>
      )}

      {/* SEO content */}
      {meta.facts && (
        <div style={{
          marginTop:48, padding:24,
          background:"var(--off-white)",
          border:"1px solid var(--rule)",
          borderRadius:"var(--r)",
        }}>
          <h2 style={{ fontSize:"1rem", fontWeight:700, marginBottom:12 }}>
            About church properties in {meta.name}
          </h2>
          <p style={{ fontSize:"0.85rem", color:"var(--ink-soft)", lineHeight:1.7 }}>
            {meta.facts}
          </p>
        </div>
      )}

      {/* Region links */}
      <div style={{ marginTop:40 }}>
        <p style={{ fontSize:"0.75rem", color:"var(--mid)", marginBottom:12,
                    letterSpacing:".08em", textTransform:"uppercase" }}>
          Other regions
        </p>
        <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
          {Object.entries(REGION_META)
            .filter(([key]) => key !== region)
            .map(([key, val]) => (
              <button key={key}
                className="btn-sm"
                onClick={() => navigate(`/churches-for-sale/${key}`)}>
                {val.name}
              </button>
            ))}
        </div>
      </div>
    </main>
  );
}
