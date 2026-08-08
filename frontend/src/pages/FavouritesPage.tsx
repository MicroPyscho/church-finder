import { useQuery, useMutation } from "@tanstack/react-query";
import { Heart, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { favouritesApi } from "../api/client";
import PropertyCard from "../components/property/PropertyCard";

export default function FavouritesPage() {
  const navigate = useNavigate();
  const { data: favs, isLoading } = useQuery({
    queryKey: ["favourites"],
    queryFn: favouritesApi.list,
  });

  const bulkMut = useMutation({
    mutationFn: favouritesApi.bulk,
    onSuccess: () => alert("Formal interest sent to all saved properties."),
  });

  if (isLoading) return (
    <div className="wrap" style={{ padding: "60px 24px", color: "var(--mid)" }}>Loading…</div>
  );

  return (
    <div className="wrap" style={{ paddingTop: 40, paddingBottom: 80 }}>

      {/* Back nav */}
      <button className="detail-back" onClick={() => navigate(-1)} style={{ marginBottom: 20 }}>
        <ArrowLeft size={13} /> Back to results
      </button>

      <div className="favs-header">
        <h1 className="favs-title">Saved properties</h1>
        <p className="favs-sub">{favs?.length ?? 0} properties saved</p>
      </div>

      {/* AI prompt — stacked on mobile */}
      {favs && favs.length > 0 && (
        <div className="favs-ai-prompt">
          <p>
            Would you like me to show formal interest in all {favs.length} saved
            properties? I'll draft and send personalised emails to each seller on your behalf.
          </p>
          <button
            className="btn btn-black"
            style={{ marginTop: 12, width: "100%", justifyContent: "center", textAlign: "center"}}
            onClick={() => bulkMut.mutate()}
            disabled={bulkMut.isPending}
          >
            {bulkMut.isPending ? "Sending…" : "Yes, contact all"}
          </button>
        </div>
      )}

      {!favs?.length ? (
        <div className="empty">
          <div className="empty__icon"><Heart size={32} strokeWidth={1} /></div>
          <div className="empty__title">No saved properties yet</div>
          <p className="empty__body">Save properties as you search and they'll appear here.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {favs.map((f: any) => (
            <PropertyCard key={f.id} property={f.property ?? f} isFaved />
          ))}
        </div>
      )}
    </div>
  );
}
