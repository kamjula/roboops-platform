function CountList({ counts, emptyLabel }) {
  const entries = Object.entries(counts ?? {}).sort(([left], [right]) => left.localeCompare(right));
  if (entries.length === 0) {
    return <p className="empty-state-message">{emptyLabel}</p>;
  }
  return (
    <ul className="analytics-count-list">
      {entries.map(([label, value]) => (
        <li key={label}>
          <span className={`analytics-status status-${label}`}>{label.replaceAll("_", " ")}</span>
          <strong>{value}</strong>
        </li>
      ))}
    </ul>
  );
}

export default function AnomalyPanel({ deterministic, statistical }) {
  return (
    <div className="analytics-grid analytics-anomaly-grid">
      <article className="analytics-panel">
        <div className="analytics-panel-heading">
          <div>
            <span className="analytics-kicker">Deterministic rules</span>
            <h2>Threshold events</h2>
          </div>
          <span className="analytics-window">{deterministic?.lookback_hours ?? 0}h window</span>
        </div>
        <CountList counts={deterministic?.severity_counts} emptyLabel="No threshold events in this window." />
        {deterministic?.anomaly_events_truncated ? (
          <p className="analytics-note">Showing the bounded event sample returned by the API.</p>
        ) : null}
      </article>

      <article className="analytics-panel">
        <div className="analytics-panel-heading">
          <div>
            <span className="analytics-kicker">Historical baseline</span>
            <h2>Statistical signals</h2>
          </div>
          <span className="analytics-window">{statistical?.baseline_hours ?? 0}h baseline</span>
        </div>
        <CountList counts={statistical?.status_counts} emptyLabel="No statistical results are available." />
        <p className="analytics-note">Latest readings are compared only with their preceding persisted history.</p>
      </article>
    </div>
  );
}
