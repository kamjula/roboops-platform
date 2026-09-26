import { useCallback, useEffect, useRef, useState } from "react";
import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import TrendPanel from "../components/analytics/TrendPanel.jsx";
import { formatSensorValue, formatTimestamp } from "../components/analytics/formatters.js";
import { getRobots, getTelemetryTrends } from "../services/api.js";

const WINDOWS = [24, 72, 168];

export default function Telemetry() {
  const [lookbackHours, setLookbackHours] = useState(24);
  const [robotId, setRobotId] = useState("");
  const [robots, setRobots] = useState([]);
  const [trends, setTrends] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  useEffect(() => {
    let active = true;
    getRobots().then((items) => { if (active) setRobots(items); }).catch(() => {
      // Trends still work when the robot list is temporarily unavailable.
    });
    return () => { active = false; };
  }, []);

  const reload = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await getTelemetryTrends({ lookbackHours, robotId: robotId || undefined });
      if (currentRequest === requestId.current) setTrends(result);
    } catch (requestError) {
      if (currentRequest === requestId.current) setError(requestError);
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [lookbackHours, robotId]);

  useEffect(() => {
    reload();
    return () => { requestId.current += 1; };
  }, [reload]);

  return (
    <section className="page telemetry-page">
      <Header title="Telemetry" />
      <div className="telemetry-heading">
        <div>
          <div className="eyebrow">Persisted sensor data</div>
          <h1>Telemetry explorer</h1>
          <p>Review bounded historical readings. Charts show sampled points; table statistics cover all readings in the selected window.</p>
        </div>
        <div className="telemetry-filters">
          <label>Robot
            <select value={robotId} onChange={(event) => setRobotId(event.target.value)}>
              <option value="">All robots</option>
              {robots.map((robot) => <option key={robot.id} value={robot.id}>{robot.robot_code || robot.name || robot.id}</option>)}
            </select>
          </label>
          <label>Time window
            <select value={lookbackHours} onChange={(event) => setLookbackHours(Number(event.target.value))}>
              {WINDOWS.map((hours) => <option key={hours} value={hours}>Last {hours} hours</option>)}
            </select>
          </label>
        </div>
      </div>

      {loading ? <LoadingState label="Loading telemetry..." /> : null}
      {!loading && error ? <ErrorState message="Unable to load telemetry. Please try again." onRetry={reload} /> : null}
      {!loading && !error && trends ? (
        <>
          <div className="telemetry-context">
            <span>{trends.total_readings} readings across {trends.series_count} sensor series</span>
            <span>Window: {formatTimestamp(trends.window_start, true)} to {formatTimestamp(trends.as_of, true)}</span>
          </div>
          <TrendPanel trends={trends} lookbackHours={lookbackHours} />
          <section className="analytics-panel">
            <div className="analytics-panel-heading"><div><span className="analytics-kicker">All returned series</span><h2>Sensor statistics</h2></div></div>
            {trends.series.length === 0 ? <p className="empty-state-message">No sensor readings in this window.</p> : (
              <div className="telemetry-table-container"><table className="telemetry-table">
                <thead><tr><th scope="col">Robot</th><th scope="col">Sensor</th><th scope="col">Readings</th><th scope="col">Minimum</th><th scope="col">Average</th><th scope="col">Maximum</th><th scope="col">Latest at</th></tr></thead>
                <tbody>{trends.series.map((item) => <tr key={item.sensor_id}>
                  <th scope="row">{item.robot_code || item.robot_name || item.robot_id}</th>
                  <td>{item.sensor_type}</td>
                  <td>{item.reading_count}</td>
                  <td>{formatSensorValue(item.min_value, item.unit)}</td>
                  <td>{formatSensorValue(item.avg_value, item.unit)}</td>
                  <td>{formatSensorValue(item.max_value, item.unit)}</td>
                  <td>{formatTimestamp(item.latest_recorded_at, true)}</td>
                </tr>)}</tbody>
              </table></div>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}
