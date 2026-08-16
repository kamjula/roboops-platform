import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

const STATUS_ORDER = ["active", "idle", "maintenance", "offline", "decommissioned"];

const STATUS_LABELS = {
  active: "Active",
  idle: "Idle",
  maintenance: "Maintenance",
  offline: "Offline",
  decommissioned: "Decommissioned",
};

const STATUS_COLORS = {
  active: "#3fb950",
  idle: "#4f8ef7",
  maintenance: "#d29922",
  offline: "#8fa0b7",
  decommissioned: "#f3565f",
};

export default function RobotStatusChart({ robotStatus } = {}) {
  if (!robotStatus) return null;

  const total = STATUS_ORDER.reduce((sum, key) => sum + (robotStatus[key] || 0), 0);

  const rows = STATUS_ORDER.map((key) => {
    const count = robotStatus[key] || 0;
    const percent = total > 0 ? Math.round((count / total) * 1000) / 10 : 0;
    return { key, label: STATUS_LABELS[key], count, percent };
  });

  return (
    <section className="dashboard-section fleet-status-section" aria-label="Fleet Status">
      <h3 className="section-title">Fleet Status</h3>
      {total === 0 ? (
        <p className="empty-state-message">No robot status data available.</p>
      ) : (
        <div className="fleet-status-content">
          <div className="fleet-status-chart">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={rows}
                  dataKey="count"
                  nameKey="label"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={2}
                >
                  {rows.map((row) => (
                    <Cell key={row.key} fill={STATUS_COLORS[row.key]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} robots`, name]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="fleet-status-legend" aria-label="Robot status breakdown">
            {rows.map((row) => (
              <li key={row.key} className="fleet-status-legend-item">
                <span
                  className="legend-swatch"
                  style={{ backgroundColor: STATUS_COLORS[row.key] }}
                  aria-hidden="true"
                />
                <span className="legend-label">{row.label}</span>
                <span className="legend-count">{row.count}</span>
                <span className="legend-percent">{row.percent}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
