export default function SummaryCards({ summary, maintenanceSummary } = {}) {
  if (!summary) return null;

  const cards = [
    ["Total Robots", summary.total_robots],
    ["Active Robots", summary.active_robots],
    ["Open Alerts", summary.open_alerts],
    ["Critical Alerts", summary.critical_alerts],
  ];

  return (
    <section className="summary-cards" aria-label="Fleet summary">
      <div className="card-grid">
        {cards.map(([label, value]) => (
          <div className="summary-card" key={label}>
            <span className="summary-card-label">{label}</span>
            <span className="summary-card-value">{value}</span>
          </div>
        ))}
      </div>
      <div className="summary-secondary">
        <div className="secondary-stat">
          <span className="secondary-label">Maintenance Due</span>
          <span className="secondary-value">{summary.maintenance_due_count}</span>
        </div>
        <div className="secondary-stat">
          <span className="secondary-label">Maintenance Overdue</span>
          <span className="secondary-value">{summary.maintenance_overdue_count}</span>
        </div>
        {maintenanceSummary ? (
          <div className="secondary-stat">
            <span className="secondary-label">Completed</span>
            <span className="secondary-value">{maintenanceSummary.completed_count}</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}
