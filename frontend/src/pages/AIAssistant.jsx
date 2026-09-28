import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import { getAlerts, getRobotHealth, getMaintenanceWorkspace } from "../services/api.js";

const QUESTIONS = ["Which robots need attention?", "What alerts are open?", "What maintenance is scheduled?"];

export default function AIAssistant() {
  const [evidence, setEvidence] = useState(null);
  const [question, setQuestion] = useState(QUESTIONS[0]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [health, alerts, maintenance] = await Promise.all([
        getRobotHealth(), getAlerts({ status: "open", limit: 200 }), getMaintenanceWorkspace({ limit: 200 }),
      ]);
      setEvidence({ health, alerts, maintenance });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { reload(); }, [reload]);

  const attention = evidence?.health.robots.filter((robot) =>
    robot.health_state === "critical" || robot.health_state === "warning") || [];
  const schedules = evidence?.maintenance.schedules.filter((item) =>
    item.status === "scheduled" || item.status === "in_progress") || [];

  return <section className="page action-page">
    <Header title="AI Assistant" />
    <div className="eyebrow">Guided fleet insights</div>
    <h2>Ask about current evidence</h2>
    <p>Choose a question to summarize database-backed signals. This guided assistant uses fixed rules; no LLM is connected. Health states are not failure predictions.</p>
    <div className="assistant-questions" aria-label="Guided questions">
      {QUESTIONS.map((item) => <button type="button" key={item} aria-pressed={question === item} onClick={() => setQuestion(item)}>{item}</button>)}
    </div>
    {loading ? <LoadingState label="Loading fleet evidence..." /> : null}
    {!loading && error ? <ErrorState message="Unable to load fleet evidence." onRetry={reload} /> : null}
    {!loading && !error && evidence ? <section className="analytics-panel" aria-live="polite">
      <h3>{question}</h3>
      {question === QUESTIONS[0] ? <>
        <p>{attention.length} of {evidence.health.robots.length} robots have a warning or critical rule-based health state.</p>
        {attention.length ? <ul className="action-list">{attention.map((robot) => <li key={robot.robot_id}>
          <strong>{robot.robot_code} · {robot.health_state}</strong>
          <span>{robot.reason_codes?.join(", ").replaceAll("_", " ") || "No reason codes"}</span>
        </li>)}</ul> : <p>No warning or critical robot states returned.</p>}
        <Link to="/health">Inspect health evidence →</Link>
      </> : null}
      {question === QUESTIONS[1] ? <>
        <p>{evidence.alerts.length}{evidence.alerts.length === 200 ? "+" : ""} open alerts returned.</p>
        {evidence.alerts.length ? <ul className="action-list">{evidence.alerts.slice(0, 5).map((alert) => <li key={alert.id}>
          <strong>{alert.robot_code} · {alert.severity}</strong><span>{alert.message}</span>
        </li>)}</ul> : <p>No open alerts returned.</p>}
        {evidence.alerts.length > 5 ? <p>Showing 5 examples; inspect the full list.</p> : null}
        <Link to="/alerts">Inspect persisted alerts →</Link>
      </> : null}
      {question === QUESTIONS[2] ? <>
        <p>{schedules.length} scheduled or in-progress items returned. Demo schedules use fixed historical dates.</p>
        {evidence.maintenance.schedule_total > evidence.maintenance.schedules.length ? <p>Only the first {evidence.maintenance.schedules.length} of {evidence.maintenance.schedule_total} schedules were checked.</p> : null}
        {schedules.length ? <ul className="action-list">{schedules.slice(0, 5).map((item) => <li key={item.id}>
          <strong>{item.robot_code} · {item.maintenance_type}</strong><span>{new Date(item.scheduled_for).toLocaleString()}</span>
        </li>)}</ul> : <p>No active schedules returned.</p>}
        {schedules.length > 5 ? <p>Showing 5 examples; inspect the full list.</p> : null}
        <Link to="/maintenance">Inspect maintenance records →</Link>
      </> : null}
    </section> : null}
  </section>;
}
