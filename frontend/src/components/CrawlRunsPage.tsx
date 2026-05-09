import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, format, differenceInSeconds } from "date-fns";
import { Activity, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { listingsApi, type CrawlRun } from "../api/client";
import clsx from "clsx";

function duration(run: CrawlRun): string {
  if (!run.finished_at) return "running…";
  const secs = differenceInSeconds(new Date(run.finished_at), new Date(run.started_at));
  return secs < 60 ? `${secs}s` : `${Math.round(secs / 60)}m ${secs % 60}s`;
}

function RunRow({ run }: { run: CrawlRun }) {
  const hasErrors = run.errors && run.errors.trim().length > 0;
  const finished  = !!run.finished_at;

  return (
    <tr className={clsx("run-row", !finished && "run-row--live")}>
      <td><code className="run-id">#{run.id}</code></td>
      <td>
        <span title={format(new Date(run.started_at), "PPpp")}>
          {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
        </span>
      </td>
      <td className="run-duration"><Clock size={12} /> {duration(run)}</td>
      <td><span className="run-stat run-stat--new">{run.new_listings}</span></td>
      <td><span className="run-stat">{run.total_scraped}</span></td>
      <td><span className="trigger-pill">{run.triggered_by}</span></td>
      <td>
        {!finished ? (
          <span className="status-pill status-pill--running">
            <span className="pulse-dot" /> Running
          </span>
        ) : hasErrors ? (
          <span className="status-pill status-pill--warn">
            <AlertCircle size={12} /> Partial
          </span>
        ) : (
          <span className="status-pill status-pill--ok">
            <CheckCircle2 size={12} /> OK
          </span>
        )}
      </td>
      <td>
        {hasErrors && (
          <details className="error-details">
            <summary>View errors</summary>
            <pre className="error-pre">{run.errors}</pre>
          </details>
        )}
      </td>
    </tr>
  );
}

export default function CrawlRunsPage() {
  const { data: runs, isLoading, isError } = useQuery({
    queryKey: ["crawl-runs"],
    queryFn:  () => listingsApi.getCrawlRuns(50),
    refetchInterval: 10_000,
  });

  const totalNew    = runs?.reduce((s, r) => s + r.new_listings, 0) ?? 0;
  const totalRuns   = runs?.length ?? 0;
  const erroredRuns = runs?.filter(r => r.errors?.trim()).length ?? 0;

  return (
    <div className="crawl-runs-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Crawl Runs</h1>
          <p className="page-subtitle">Audit log — every scrape job, every result</p>
        </div>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-card__num">{totalRuns}</span>
          <span className="stat-card__label">Total Runs</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__num stat-card__num--green">{totalNew}</span>
          <span className="stat-card__label">New Listings Found</span>
        </div>
        <div className="stat-card">
          <span className={clsx("stat-card__num", erroredRuns > 0 && "stat-card__num--amber")}>
            {erroredRuns}
          </span>
          <span className="stat-card__label">Runs w/ Errors</span>
        </div>
      </div>

      <div className="table-wrap">
        <table className="runs-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Started</th>
              <th>Duration</th>
              <th>New</th>
              <th>Scraped</th>
              <th>Triggered By</th>
              <th>Status</th>
              <th>Errors</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={8} className="table-loading">
                  <Activity size={16} className="spin" /> Loading runs…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={8}>
                  <div className="alert alert--error">Failed to load crawl runs.</div>
                </td>
              </tr>
            )}
            {runs?.map(r => <RunRow key={r.id} run={r} />)}
            {runs?.length === 0 && !isLoading && (
              <tr>
                <td colSpan={8} className="table-empty">
                  <Activity size={28} strokeWidth={1} />
                  <p>No crawl runs yet. Trigger one from the Listings page.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
