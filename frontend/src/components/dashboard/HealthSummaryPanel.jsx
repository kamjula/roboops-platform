const STATUS_ORDER = ["active", "idle", "maintenance", "offline", "decommissioned"];

const STATUS_LABELS = {
  active: "Active",
  idle: "Idle",
  maintenance: "Maintenance",
  offline: "Offline",
  decommissioned: "Decommissioned",
};

export default function HealthSummaryPanel({ healthSummary } = {}) {
  if (!healthSummary) {
    return (
      <section className="dashboard-section health-summary-section" aria-label="Robot Health">
        <h3 className="section-title">Robot Health</h3>
        <p className="empty-state-message">Health data unavailable.</p>
      </section>
    );
  }

  const {
    average_health_value: averageHealthValue,
    health_metric_available: healthMetricAvailable,
    robot_status_counts: statusCounts,
    maintenance_due_count: dueCount,
    maintenance_overdue_count: overdueCount,
  } = healthSummary;

  return (
    <section className="dashboard-section health-summary-section" aria-label="Robot Health">
      <h3 className="section-title">Robot Health</h3>
      <div className="health-metric-row">
        {healthMetricAvailable && typeof averageHealthValue === "number" ? (
          <span className="health-metric-value">{averageHealthValue}</span>
        ) : (
          <p className="empty-state-message health-metric-unavailable">
            Aggregate health metric is not currently available.
          </p>
        )}
      </div>
      {statusCounts ? (
        <ul className="health-status-breakdown" aria-label="Robot status breakdown">
          {STATUS_ORDER.map((key) => (
            <li key={key} className="health-status-item">
              <span className="health-status-label">{STATUS_LABELS[key]}</span>
              <span className="health-status-count">{statusCounts[key] || 0}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="health-maintenance-context">
        <div className="health-maintenance-stat">
          <span className="secondary-label">Maintenance Due</span>
          <span className="secondary-value">{dueCount ?? 0}</span>
        </div>
        <div className="health-maintenance-stat health-maintenance-overdue">
          <span className="secondary-label">Maintenance Overdue</span>
          <span className="secondary-value">{overdueCount ?? 0}</span>
        </div>
      </div>
    </section>
  );
}
