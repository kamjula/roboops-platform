import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import Header from "../components/layout/Header.jsx";
import { getAlerts, resolveAlert } from "../services/api.js";

function formatTimestamp(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
}

export default function Alerts() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [severityFilter, setSeverityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);
  const [mutationError, setMutationError] = useState(null);
  const canResolve = user?.role === "operator" || user?.role === "admin";

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAlerts(await getAlerts({ status: statusFilter, severity: severityFilter || undefined }));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleResolve = async (alertId) => {
    if (resolvingId) return;
    setResolvingId(alertId);
    setMutationError(null);
    try {
      const resolved = await resolveAlert(alertId);
      if (statusFilter === "open") {
        setAlerts((current) => current.filter((alert) => alert.id !== alertId));
      } else {
        setAlerts((current) => current.map((alert) => (
          alert.id === alertId ? { ...alert, resolved_at: resolved.resolved_at } : alert
        )));
      }
    } catch (requestError) {
      setMutationError(requestError.status === 403
        ? "You do not have permission to resolve alerts."
        : "Unable to resolve the alert. Please try again.");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <section className="page alerts-page">
      <Header title="Alerts" />
      <div className="alerts-heading">
        <div>
          <div className="eyebrow">Fleet operations</div>
          <h2>Alert lifecycle</h2>
          <p>Review persisted operational alerts and resolve investigated events.</p>
        </div>
        {!loading && !error ? <strong>{alerts.length} alerts</strong> : null}
      </div>
      <div className="alert-filters" aria-label="Alert filters">
        <label>Status
          <select aria-label="Status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="open">Open</option><option value="resolved">Resolved</option><option value="all">All</option>
          </select>
        </label>
        <label>Severity
          <select aria-label="Severity" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            <option value="">All</option><option value="critical">Critical</option><option value="warning">Warning</option><option value="info">Info</option>
          </select>
        </label>
      </div>
      {mutationError ? <div className="alert-mutation-error" role="alert">{mutationError}</div> : null}
      {loading ? <LoadingState label="Loading alerts..." /> : null}
      {!loading && error ? <ErrorState message="Unable to load alerts. Please try again." onRetry={loadAlerts} /> : null}
      {!loading && !error && alerts.length === 0 ? <div className="state-panel"><p>No alerts match these filters.</p></div> : null}
      {!loading && !error && alerts.length > 0 ? (
        <div className="alerts-table-container">
          <table className="alerts-table">
            <thead><tr><th>Severity</th><th>Robot</th><th>Type</th><th>Message</th><th>Triggered</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{alerts.map((alert) => (
              <tr key={alert.id}>
                <td><span className={`alert-severity-badge severity-${alert.severity}`}>{alert.severity}</span></td>
                <td><strong>{alert.robot_code}</strong><small>{alert.robot_name}</small></td>
                <td>{alert.alert_type}</td><td>{alert.message}</td><td>{formatTimestamp(alert.triggered_at)}</td>
                <td>{alert.resolved_at ? `Resolved ${formatTimestamp(alert.resolved_at)}` : "Open"}</td>
                <td>{!alert.resolved_at && canResolve ? (
                  <button type="button" className="resolve-alert-button" disabled={Boolean(resolvingId)} onClick={() => handleResolve(alert.id)}>
                    {resolvingId === alert.id ? "Resolving..." : "Resolve"}
                  </button>
                ) : "-"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
