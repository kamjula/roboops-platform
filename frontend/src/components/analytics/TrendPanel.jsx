import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatSensorValue, formatTimestamp } from "./formatters.js";

export default function TrendPanel({ trends, lookbackHours = 24 }) {
  const series = trends?.series ?? [];
  return (
    <section className="analytics-panel analytics-trends-panel">
      <div className="analytics-panel-heading">
        <div>
          <span className="analytics-kicker">Persisted telemetry</span>
          <h2>Sensor trends</h2>
        </div>
        <span className="analytics-window">API-wide total: {trends?.total_readings ?? 0} readings</span>
      </div>
      {series.length === 0 ? (
        <p className="empty-state-message">No telemetry series are available for this window.</p>
      ) : (<>
        {series.length > 4 ? <p className="analytics-note">Showing 4 of {series.length} series. The reading total covers all series.</p> : null}
        <div className="trend-grid">
          {series.slice(0, 4).map((item) => (
            <article className="trend-card" key={item.sensor_id}>
              <div className="trend-card-heading">
                <div>
                  <strong>{item.robot_code}</strong>
                  <span>{item.sensor_type} · {item.unit}</span>
                </div>
                <div className="trend-latest">
                  <strong>{formatSensorValue(item.latest_value, item.unit)}</strong>
                  <span>latest</span>
                </div>
              </div>
              <div className="trend-chart" aria-label={`${item.robot_code} ${item.sensor_type} trend`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={item.points} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="#223044" strokeDasharray="3 3" />
                    <XAxis dataKey="recorded_at" tickFormatter={(value) => formatTimestamp(value, lookbackHours > 24)} minTickGap={28} stroke="#71839a" fontSize={10} />
                    <YAxis domain={["auto", "auto"]} tickFormatter={(value) => formatSensorValue(value, item.unit)} stroke="#71839a" fontSize={10} />
                    <Tooltip
                      labelFormatter={(value) => formatTimestamp(value, true)}
                      formatter={(value) => [formatSensorValue(value, item.unit), item.sensor_type]}
                      contentStyle={{ background: "#0f1620", border: "1px solid #304158", borderRadius: 8 }}
                    />
                    <Line dataKey="value" type="monotone" stroke="#76a8ff" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </article>
          ))}
        </div>
      </>)}
      {trends?.points_truncated ? <p className="analytics-note">Charts use the API's bounded point sample.</p> : null}
    </section>
  );
}
