export default function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div className="cards">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skel-card skeleton" style={{ animationDelay:`${i*0.08}s` }} />
      ))}
    </div>
  );
}
