import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import { getAlerts, getMaintenanceWorkspace } from "../services/api.js";

export default function Tasks() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [alerts, maintenance] = await Promise.all([
        getAlerts({ status: "open", limit: 200 }), getMaintenanceWorkspace({ limit: 200 }),
      ]);
      setData({ alerts, maintenance });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { reload(); }, [reload]);

  const schedules = data?.maintenance.schedules.filter((item) =>
    item.status === "scheduled" || item.status === "in_progress") || [];
  const when = (value) => new Date(value).toLocaleString();

  return <section className="page action-page">
    <Header title="Tasks" />
    <div className="eyebrow">Operational review queue</div>
    <h2>Items to review</h2>
    <p>This read-only queue is derived from open alerts and scheduled maintenance. It does not create or complete task records.</p>
    {loading ? <LoadingState label="Loading review queue..." /> : null}
    {!loading && error ? <ErrorState message="Unable to load review queue." onRetry={reload} /> : null}
    {!loading && !error && data ? <>
      <section className="analytics-panel" aria-label="Open alert actions">
        <h3>Open alerts ({data.alerts.length}{data.alerts.length === 200 ? "+" : ""})</h3>
        {data.alerts.length === 0 ? <p>No open alerts returned.</p> : <ul className="action-list">
          {data.alerts.map((item) => <li key={item.id}>
            <strong>{item.robot_code} · {item.severity}</strong>
            <span>{item.message}</span><small>{when(item.triggered_at)}</small>
          </li>)}
        </ul>}
        <Link to="/alerts">Review alerts →</Link>
      </section>
      <section className="analytics-panel" aria-label="Scheduled maintenance actions">
        <h3>Scheduled or in progress ({schedules.length}{data.maintenance.schedule_total > data.maintenance.schedules.length ? "+" : ""})</h3>
        <p>Synthetic seed schedules use fixed historical dates. They are examples, not live dispatch orders.</p>
        {schedules.length === 0 ? <p>No active schedules returned.</p> : <ul className="action-list">
          {schedules.map((item) => <li key={item.id}>
            <strong>{item.robot_code} · {item.maintenance_type}</strong>
            <span>{item.status.replaceAll("_", " ")}</span><small>{when(item.scheduled_for)}</small>
          </li>)}
        </ul>}
        <Link to="/maintenance">Review maintenance →</Link>
      </section>
    </> : null}
  </section>;
}
