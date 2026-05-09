import { useQuery } from "@tanstack/react-query";
import { healthApi } from "../api/client";
import clsx from "clsx";

export default function HealthBadge() {
  const { data, isError } = useQuery({
    queryKey:       ["health"],
    queryFn:        healthApi.get,
    refetchInterval: 30_000,
    retry:          1,
  });

  const ok = !isError && data?.status === "ok" && data?.db === "ok";

  return (
    <div className={clsx("health-badge", ok ? "health-badge--ok" : "health-badge--err")}
      title={data ? `API ${data.status} | DB ${data.db} | v${data.version}` : "API unreachable"}
    >
      <span className="health-dot" />
      {ok ? "API OK" : "API ⚠"}
    </div>
  );
}
