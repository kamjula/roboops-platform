import { useCallback, useEffect, useState } from "react";
import ErrorState from "../components/common/ErrorState.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import Header from "../components/layout/Header.jsx";
import { getMaintenanceWorkspace } from "../services/api.js";

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}

export default function Maintenance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setData(await getMaintenanceWorkspace());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return <section className="page maintenance-page">
    <Header title="Maintenance" />
    <div className="alerts-heading">
      <div>
        <div className="eyebrow">Fleet operations</div>
        <h2>Schedules & service history</h2>
        <p>Read-only records from the fleet database. The demo uses synthetic, fixed-date seed data; historical dates are not current work orders.</p>
      </div>
    </div>
    {loading ? <LoadingState label="Loading maintenance records..." /> : null}
    {!loading && error ? <ErrorState message="Unable to load maintenance records." onRetry={load} /> : null}
    {!loading && !error && data ? <>
      <section aria-label="Maintenance schedules">
        <h3>Schedules ({data.schedule_total})</h3>
        {data.schedule_total > data.schedules.length ? <p>Showing first {data.schedules.length} of {data.schedule_total} schedules by date.</p> : null}
        {data.schedules.length === 0 ? <div className="state-panel">No schedules recorded.</div> :
          <div className="alerts-table-container"><table className="alerts-table">
            <thead><tr><th>Robot</th><th>Type</th><th>Scheduled for</th><th>Status</th><th>Notes</th></tr></thead>
            <tbody>{data.schedules.map((item) => <tr key={item.id}>
              <td><strong>{item.robot_code}</strong><small>{item.robot_name}</small></td>
              <td>{item.maintenance_type}</td><td>{formatDate(item.scheduled_for)}</td>
              <td>{item.status.replaceAll("_", " ")}</td><td>{item.notes || "—"}</td>
            </tr>)}</tbody>
          </table></div>}
      </section>
      <section aria-label="Completed maintenance records">
        <h3>Service history ({data.record_total})</h3>
        {data.record_total > data.records.length ? <p>Showing latest {data.records.length} of {data.record_total} records.</p> : null}
        {data.records.length === 0 ? <div className="state-panel">No completed service recorded.</div> :
          <div className="alerts-table-container"><table className="alerts-table">
            <thead><tr><th>Robot</th><th>Type</th><th>Performed</th><th>Technician</th><th>Description</th><th>Cost (USD)</th></tr></thead>
            <tbody>{data.records.map((item) => <tr key={item.id}>
              <td><strong>{item.robot_code}</strong><small>{item.robot_name}</small></td>
              <td>{item.maintenance_type}</td><td>{formatDate(item.performed_at)}</td>
              <td>{item.technician_name}</td><td>{item.description || "—"}</td>
              <td>{item.cost_usd == null ? "—" : `$${item.cost_usd.toFixed(2)}`}</td>
            </tr>)}</tbody>
          </table></div>}
      </section>
    </> : null}
  </section>;
}
