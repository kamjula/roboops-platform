import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function TrendPanel({ trends }) {
  const series = trends?.series ?? [];
  return (
    <section className="analytics-panel analytics-trends-panel">
      <div className="analytics-panel-heading">
        <div>
          <span className="analytics-kicker">Persisted telemetry</span>
          <h2>Sensor trends</h2>
        </div>
        <span className="analytics-window">{trends?.total_readings ?? 0} readings</span>
      </div>
      {series.length === 0 ? (
        <p className="empty-state-message">No telemetry series are available for this window.</p>
      ) : (
        <div className="trend-grid">
          {series.slice(0, 4).map((item) => (
            <article className="trend-card" key={item.sensor_id}>
              <div className="trend-card-heading">
                <div>
                  <strong>{item.robot_code}</strong>
                  <span>{item.sensor_type} · {item.unit}</span>
                </div>
                <div className="trend-latest">
                  <strong>{item.latest_value}</strong>
                  <span>latest</span>
                </div>
              </div>
              <div className="trend-chart" aria-label={`${item.robot_code} ${item.sensor_type} trend`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={item.points} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="#223044" strokeDasharray="3 3" />
                    <XAxis dataKey="recorded_at" tickFormatter={formatTime} minTickGap={28} stroke="#71839a" fontSize={10} />
                    <YAxis domain={["auto", "auto"]} stroke="#71839a" fontSize={10} />
                    <Tooltip
                      labelFormatter={formatTime}
                      contentStyle={{ background: "#0f1620", border: "1px solid #304158", borderRadius: 8 }}
                    />
                    <Line dataKey="value" type="monotone" stroke="#76a8ff" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </article>
          ))}
        </div>
      )}
      {trends?.points_truncated ? <p className="analytics-note">Charts use the API's bounded point sample.</p> : null}
    </section>
  );
}
