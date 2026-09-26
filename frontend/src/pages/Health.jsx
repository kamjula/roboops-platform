import { useCallback, useEffect, useState } from "react";
import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import { getRobotHealth } from "../services/api.js";

const STATES = ["critical", "warning", "unknown", "healthy"];

function sensorLabel(sensor) {
  if (!sensor) return "No reading available";
  const value = typeof sensor.value === "number" && Number.isFinite(sensor.value)
    ? `${sensor.value.toFixed(2)}${sensor.unit ? ` ${sensor.unit}` : ""}`
    : "No reading available";
  return `${value} · ${sensor.freshness || "unknown freshness"} · ${sensor.state || "unknown"}`;
}

function reasonLabel(reasons) {
  return reasons?.length ? reasons.map((reason) => reason.replaceAll("_", " ")).join(", ") : "No reason codes";
}

export default function Health() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getRobotHealth());
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const robots = data?.robots || [];
  const counts = Object.fromEntries(STATES.map((state) => [state, robots.filter((robot) => robot.health_state === state).length]));
  const ordered = [...robots].sort((a, b) =>
    (STATES.indexOf(a.health_state) === -1 ? STATES.length : STATES.indexOf(a.health_state))
      - (STATES.indexOf(b.health_state) === -1 ? STATES.length : STATES.indexOf(b.health_state))
      || (a.robot_code || "").localeCompare(b.robot_code || ""));

  return (
    <section className="page health-page">
      <Header title="Health" />
      <div className="health-heading">
        <div className="eyebrow">Latest persisted sensor readings</div>
        <h1>Fleet health</h1>
        <p>Rule-based battery and temperature states. These are current signals, not failure predictions.</p>
      </div>
      {loading ? <LoadingState label="Loading fleet health..." /> : null}
      {!loading && error ? <ErrorState message="Unable to load fleet health." onRetry={reload} /> : null}
      {!loading && !error && data ? (
        <>
          <div className="health-context">
            <span>As of {new Date(data.as_of).toLocaleString()}</span>
            <span>Freshness threshold: {data.freshness_threshold_seconds} seconds</span>
          </div>
          <div className="health-cards" aria-label="Health state counts">
            {STATES.map((state) => <div className="health-card" key={state}><span>{state}</span><strong>{counts[state]}</strong></div>)}
          </div>
          {robots.length === 0 ? <div className="state-panel">No robots found in the fleet.</div> : (
            <div className="health-table-container">
              <table className="health-table">
                <thead><tr><th scope="col">Robot</th><th scope="col">Operational</th><th scope="col">Health</th><th scope="col">Battery</th><th scope="col">Temperature</th><th scope="col">Reason</th></tr></thead>
                <tbody>{ordered.map((robot) => <tr key={robot.robot_id}>
                  <th scope="row">{robot.robot_code || robot.robot_name || robot.robot_id}<small>{robot.robot_name}</small></th>
                  <td>{robot.operational_status?.replaceAll("_", " ") || "Unknown"}</td>
                  <td><span className={`analytics-status status-${robot.health_state || "unknown"}`}>{robot.health_state || "unknown"}</span></td>
                  <td>{sensorLabel(robot.battery)}</td>
                  <td>{sensorLabel(robot.temperature)}</td>
                  <td>{reasonLabel(robot.reason_codes)}</td>
                </tr>)}</tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
