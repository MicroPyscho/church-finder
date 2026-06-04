import { useState } from "react";

const INTENTS = [
  {v:"buy_use",      l:"Use as a church or place of worship"},
  {v:"buy_religious",l:"Other religious or community purpose"},
  {v:"buy_convert",  l:"Convert to commercial or residential"},
  {v:"buy_preserve", l:"Buy and preserve / restore"},
  {v:"explore",      l:"Just exploring"},
];

const LISTING_TYPES = [
  {v:"any",    l:"All — sale, auction, lease"},
  {v:"sale",   l:"Private sale only"},
  {v:"auction",l:"Auction only"},
];

const FEATURES = [
  {v:"parking",      l:"🅿️ Parking"},
  {v:"graveyard",    l:"⚰️ Graveyard"},
  {v:"balcony",      l:"🪟 Balcony / gallery"},
  {v:"porch",        l:"🚪 Porch"},
  {v:"hall",         l:"🏛 Parish hall"},
  {v:"spire",        l:"⛪ Spire / tower"},
  {v:"organ",        l:"🎵 Organ"},
  {v:"vestry",       l:"📦 Vestry"},
  {v:"stage",        l:"🎭 Stage"},
  {v:"kitchen",      l:"🍽️ Kitchen"},
  {v:"high_ceiling", l:"🏔️ High ceilings"},
  {v:"stained_glass",l:"🌈 Stained glass"},
  {v:"bell_tower",   l:"🔔 Bell tower"},
];

interface Props { intent:any; questions:string[]; onComplete:(f:any)=>void; onSkip:()=>void; }

export default function FollowUpFlow({ intent, onComplete, onSkip }:Props) {
  const [step,    setStep]   = useState(0);
  const [selInt,  setSelInt] = useState(intent?.intent_type??"");
  const [selFts,  setSelFts] = useState<string[]>(intent?.features??[]);
  const [selType, setSelType]= useState("any");

  const toggleFeat = (v:string) => setSelFts(f => f.includes(v)?f.filter(x=>x!==v):[...f,v]);

  const STEPS = [
    {
      q:"What would you like to use it for?",
      body: (
        <div className="followup__opts">
          {INTENTS.map(o=>(
            <button key={o.v} className={`followup__opt${selInt===o.v?" sel":""}`} onClick={()=>setSelInt(o.v)}>{o.l}</button>
          ))}
        </div>
      ),
    },
    {
      q:"Any specific features you need?",
      body: (
        <div className="followup__opts">
          {FEATURES.map(o=>(
            <button key={o.v} className={`followup__opt${selFts.includes(o.v)?" sel":""}`} onClick={()=>toggleFeat(o.v)}>{o.l}</button>
          ))}
        </div>
      ),
    },
    {
      q:"Include auction properties?",
      body: (
        <div className="followup__opts">
          {LISTING_TYPES.map(o=>(
            <button key={o.v} className={`followup__opt${selType===o.v?" sel":""}`} onClick={()=>setSelType(o.v)}>{o.l}</button>
          ))}
        </div>
      ),
    },
  ];

  const cur    = STEPS[step];
  const isLast = step===STEPS.length-1;

  return (
    <div className="followup">
      <div className="followup__card">
        <div style={{display:"flex",gap:4,marginBottom:14}}>
          {STEPS.map((_,i)=>(
            <div key={i} style={{width:i===step?20:6,height:4,borderRadius:2,background:i<=step?"var(--ink)":"var(--rule)",transition:"all .2s"}}/>
          ))}
        </div>
        <p className="followup__q">{cur.q}</p>
        {cur.body}
        <div className="followup__nav">
          {isLast
            ? <button className="btn-next" onClick={()=>onComplete({intent:selInt,features:selFts,listing_type:selType})}>Show results →</button>
            : <button className="btn-next" onClick={()=>setStep(s=>s+1)}>Next →</button>
          }
          <button className="btn-skip" onClick={onSkip}>Skip — show results</button>
        </div>
      </div>
    </div>
  );
}
