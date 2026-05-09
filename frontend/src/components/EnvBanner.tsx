const ENV = import.meta.env.VITE_APP_ENV ?? "dev";

const MESSAGES: Record<string, string> = {
  dev:     "⚙ Development environment — data is not real",
  staging: "🔬 Staging environment — pre-production preview",
};

export function EnvBanner() {
  if (ENV === "prod") return null;

  return (
    <div className={`env-banner env-banner--${ENV}`}>
      {MESSAGES[ENV] ?? `Environment: ${ENV}`}
    </div>
  );
}

export default EnvBanner;
