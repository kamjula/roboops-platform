function count(map, key) {
  return map?.[key] ?? 0;
}

export default function AnalyticsSummary({ deterministic, statistical, conditions }) {
  const conditionRobots = conditions?.robots ?? [];
  const conditionCounts = conditionRobots.reduce(
    (totals, robot) => ({ ...totals, [robot.status]: (totals[robot.status] ?? 0) + 1 }),
    {},
  );
  const deterministicEvents = Object.values(deterministic?.severity_counts ?? {})
    .reduce((total, value) => total + value, 0);
  const statisticalFlags = count(statistical?.status_counts, "warning")
    + count(statistical?.status_counts, "critical")
    + count(statistical?.status_counts, "anomaly");

  const cards = [
    ["Readings evaluated", deterministic?.total_readings ?? 0],
    ["Rule-based events", deterministicEvents],
    ["Statistical flags", statisticalFlags],
    ["Condition warnings", count(conditionCounts, "warning") + count(conditionCounts, "critical")],
  ];

  return (
    <section aria-label="Analytics summary" className="analytics-summary-grid">
      {cards.map(([label, value]) => (
        <article className="analytics-summary-card" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </section>
  );
}
