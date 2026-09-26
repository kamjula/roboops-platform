function displayScore(score) {
  return score === null || score === undefined ? "Unavailable" : Number(score).toFixed(2);
}

export default function ConditionTable({ conditions, trends }) {
  const robots = conditions?.robots ?? [];
  const robotCodes = new Map((trends?.series ?? []).map(({ robot_id, robot_code }) => [robot_id, robot_code]));
  return (
    <section className="analytics-panel">
      <div className="analytics-panel-heading">
        <div>
          <span className="analytics-kicker">Unsupervised condition scoring</span>
          <h2>Fleet condition</h2>
        </div>
        <span className="analytics-window">{conditions?.condition_model_version ?? "model unavailable"}</span>
      </div>
      <p className="analytics-disclaimer">
        These scores describe unusual telemetry conditions. They are not failure probabilities or remaining-useful-life estimates.
      </p>
      {robots.length === 0 ? (
        <p className="empty-state-message">No robot has enough telemetry history for condition scoring.</p>
      ) : (
        <div className="analytics-table-container">
          <table className="analytics-table">
            <thead>
              <tr><th>Robot</th><th>Status</th><th>Score</th><th>Baseline rows</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {robots.map((robot) => (
                <tr key={robot.robot_id}>
                  <td title={robot.robot_id}>{robotCodes.get(robot.robot_id) ?? `${robot.robot_id.slice(0, 8)} (code unavailable)`}</td>
                  <td><span className={`analytics-status status-${robot.status}`}>{robot.status}</span></td>
                  <td>{displayScore(robot.score)}</td>
                  <td>{robot.baseline_row_count}</td>
                  <td>{robot.reason.replaceAll("_", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
