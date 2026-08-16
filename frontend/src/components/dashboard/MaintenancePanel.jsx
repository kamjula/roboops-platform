const MAINTENANCE_FIELDS = [
  { key: "scheduled_count", label: "Scheduled" },
  { key: "in_progress_count", label: "In Progress" },
  { key: "due_count", label: "Due" },
  { key: "overdue_count", label: "Overdue" },
  { key: "completed_count", label: "Completed" },
];

function formatAsOf(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function MaintenancePanel({ maintenanceSummary } = {}) {
  if (!maintenanceSummary) {
    return (
      <section className="dashboard-section maintenance-section" aria-label="Maintenance">
        <h3 className="section-title">Maintenance</h3>
        <p className="empty-state-message">Maintenance data unavailable.</p>
      </section>
    );
  }

  const asOfLabel = formatAsOf(maintenanceSummary.as_of);

  return (
    <section className="dashboard-section maintenance-section" aria-label="Maintenance">
      <h3 className="section-title">Maintenance</h3>
      <ul className="maintenance-counts">
        {MAINTENANCE_FIELDS.map(({ key, label }) => (
          <li
            key={key}
            className={`maintenance-count-item${key === "overdue_count" ? " maintenance-overdue" : ""}`}
          >
            <span className="maintenance-count-label">{label}</span>
            <span className="maintenance-count-value">{maintenanceSummary[key] ?? 0}</span>
          </li>
        ))}
      </ul>
      {asOfLabel ? <p className="maintenance-as-of">Updated as of {asOfLabel}</p> : null}
    </section>
  );
}
