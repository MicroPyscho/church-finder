const SUGGESTIONS = [
  "Church for sale in Kent",
  "Former chapel with parking, Yorkshire",
  "Community hall large capacity, auction",
  "Methodist church under £200k, Midlands",
];

interface Props { data:any; onSuggestionClick:(s:string)=>void; }

export default function EdgeCase({ data, onSuggestionClick }:Props) {
  return (
    <div className="edge-case">
      <span className="edge-case__icon">⛪</span>
      <h2 className="edge-case__title">We specialise in churches and gathering spaces</h2>
      <p className="edge-case__body">
        {data.message ?? "Nave covers churches, chapels, halls, and large gathering spaces across the UK. Expanding to more property types soon."}
      </p>
      <p style={{fontSize:"0.75rem",color:"var(--mid)",marginBottom:10,fontWeight:500,letterSpacing:".08em",textTransform:"uppercase"}}>Try one of these</p>
      <div className="edge-case__suggestions">
        {SUGGESTIONS.map(s => (
          <button key={s} className="edge-suggestion" onClick={()=>onSuggestionClick(s)}>{s}</button>
        ))}
      </div>
    </div>
  );
}
