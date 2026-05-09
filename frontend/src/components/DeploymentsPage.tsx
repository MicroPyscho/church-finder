import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow, format } from "date-fns";
import {
  Rocket, RotateCcw, CheckCircle2, Circle,
  AlertTriangle, ChevronDown, ChevronUp,
} from "lucide-react";
import { deploymentsApi, type Deployment } from "../api/client";
import clsx from "clsx";

const ENVS = ["prod", "staging", "dev"] as const;

const ENV_COLOUR: Record<string, string> = {
  prod:    "env--prod",
  staging: "env--staging",
  dev:     "env--dev",
};

function RollbackModal({
  target,
  onConfirm,
  onCancel,
  isPending,
}: {
  target:    Deployment;
  onConfirm: (reason: string) => void;
  onCancel:  () => void;
  isPending: boolean;
}) {
  const [reason, setReason] = useState("");

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal__header">
          <AlertTriangle size={20} className="modal__warn-icon" />
          <h3>Confirm Rollback</h3>
        </div>
        <p className="modal__body">
          Roll back <strong>{target.environment}</strong> to version{" "}
          <code>{target.version}</code>?
          <br />
          <span className="modal__detail">
            Image: <code>{target.image_tag}</code>
            <br />
            Originally deployed{" "}
            {formatDistanceToNow(new Date(target.deployed_at), { addSuffix: true })} by{" "}
            <em>{target.deployed_by}</em>
          </span>
        </p>
        <textarea
          className="modal__reason"
          placeholder="Reason for rollback (optional)"
          value={reason}
          onChange={e => setReason(e.target.value)}
          rows={2}
        />
        <div className="modal__actions">
          <button className="btn btn--ghost" onClick={onCancel} disabled={isPending}>
            Cancel
          </button>
          <button
            className={clsx("btn btn--danger", isPending && "btn--loading")}
            onClick={() => onConfirm(reason)}
            disabled={isPending}
          >
            <RotateCcw size={14} />
            {isPending ? "Rolling back…" : "Roll Back Now"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeployRow({
  deploy,
  onRollback,
}: {
  deploy:     Deployment;
  onRollback: (d: Deployment) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className={clsx("deploy-row", deploy.is_current && "deploy-row--current")}>
        <td>
          <span className={clsx("env-pill", ENV_COLOUR[deploy.environment])}>
            {deploy.environment}
          </span>
        </td>
        <td>
          <code className="version-code">{deploy.version.slice(0, 12)}</code>
        </td>
        <td className="deploy-row__image">
          <code>{deploy.image_tag}</code>
        </td>
        <td>{deploy.deployed_by}</td>
        <td>
          <span title={format(new Date(deploy.deployed_at), "PPpp")}>
            {formatDistanceToNow(new Date(deploy.deployed_at), { addSuffix: true })}
          </span>
        </td>
        <td>
          {deploy.is_current ? (
            <span className="status-pill status-pill--live">
              <CheckCircle2 size={12} /> Live
            </span>
          ) : (
            <span className="status-pill status-pill--old">
              <Circle size={12} /> Prev
            </span>
          )}
          {deploy.rollback_of && (
            <span className="status-pill status-pill--rollback">
              <RotateCcw size={11} /> Rollback
            </span>
          )}
        </td>
        <td className="deploy-row__actions">
          {!deploy.is_current && (
            <button
              className="btn btn--rollback"
              onClick={() => onRollback(deploy)}
              title="Roll back to this version"
            >
              <RotateCcw size={13} /> Rollback
            </button>
          )}
          {deploy.notes && (
            <button
              className="btn btn--icon"
              onClick={() => setExpanded(e => !e)}
              aria-label="Toggle notes"
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          )}
        </td>
      </tr>
      {expanded && deploy.notes && (
        <tr className="deploy-row__notes-row">
          <td colSpan={7}>
            <span className="deploy-notes">{deploy.notes}</span>
          </td>
        </tr>
      )}
    </>
  );
}

export default function DeploymentsPage() {
  const qc = useQueryClient();
  const [envFilter, setEnvFilter]           = useState<string>("");
  const [rollbackTarget, setRollbackTarget] = useState<Deployment | null>(null);
  const [successMsg, setSuccessMsg]         = useState("");

  const { data: deploys, isLoading, isError } = useQuery({
    queryKey: ["deployments", envFilter],
    queryFn:  () => deploymentsApi.getAll(envFilter || undefined),
    refetchInterval: 15_000,
  });

  const rollbackMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      deploymentsApi.rollback(id, reason),
    onSuccess: (res) => {
      setRollbackTarget(null);
      setSuccessMsg(res.message);
      qc.invalidateQueries({ queryKey: ["deployments"] });
      setTimeout(() => setSuccessMsg(""), 6000);
    },
  });

  return (
    <div className="deployments-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Deployments</h1>
          <p className="page-subtitle">Full history — roll back any version in one click</p>
        </div>

        <div className="env-filter">
          {["", ...ENVS].map(env => (
            <button
              key={env || "all"}
              className={clsx("btn btn--ghost env-filter__btn",
                envFilter === env && "env-filter__btn--active")}
              onClick={() => setEnvFilter(env)}
            >
              {env || "All"}
            </button>
          ))}
        </div>
      </div>

      {successMsg && (
        <div className="alert alert--success">
          <CheckCircle2 size={15} /> {successMsg}
        </div>
      )}

      {rollbackMutation.isError && (
        <div className="alert alert--error">
          Rollback failed — check the logs.
        </div>
      )}

      <div className="table-wrap">
        <table className="deploy-table">
          <thead>
            <tr>
              <th>Env</th>
              <th>Version</th>
              <th>Image</th>
              <th>By</th>
              <th>When</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="table-loading">Loading…</td></tr>
            )}
            {isError && (
              <tr>
                <td colSpan={7}>
                  <div className="alert alert--error">Failed to load deployments.</div>
                </td>
              </tr>
            )}
            {deploys?.map(d => (
              <DeployRow key={d.id} deploy={d} onRollback={setRollbackTarget} />
            ))}
            {deploys?.length === 0 && (
              <tr>
                <td colSpan={7} className="table-empty">
                  <Rocket size={28} strokeWidth={1} />
                  <p>No deployments recorded yet.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {rollbackTarget && (
        <RollbackModal
          target={rollbackTarget}
          onConfirm={(reason) =>
            rollbackMutation.mutate({ id: rollbackTarget.id, reason })
          }
          onCancel={() => setRollbackTarget(null)}
          isPending={rollbackMutation.isPending}
        />
      )}
    </div>
  );
}
