const SEVERITY_LABELS = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
};

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function RecentAlerts({ alerts } = {}) {
  const list = Array.isArray(alerts) ? alerts : [];

  return (
    <section className="dashboard-section recent-alerts-section" aria-label="Recent Alerts">
      <h3 className="section-title">Recent Alerts</h3>
      {list.length === 0 ? (
        <p className="empty-state-message">No recent alerts.</p>
      ) : (
        <ul className="alerts-list">
          {list.map((alert) => (
            <li key={alert.id} className={`alert-item severity-${alert.severity || "unknown"}`}>
              <span className="alert-severity-badge">
                {SEVERITY_LABELS[alert.severity] || alert.severity || "Unknown"}
              </span>
              <div className="alert-details">
                <div className="alert-robot">
                  {alert.robot_code ? (
                    <span className="alert-robot-code">{alert.robot_code}</span>
                  ) : null}
                  {alert.robot_name ? (
                    <span className="alert-robot-name">{alert.robot_name}</span>
                  ) : null}
                </div>
                <div className="alert-message">
                  {alert.alert_type ? (
                    <span className="alert-type">{alert.alert_type}</span>
                  ) : null}
                  {alert.message ? <span className="alert-text">{alert.message}</span> : null}
                </div>
              </div>
              <span className="alert-timestamp">{formatTimestamp(alert.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
