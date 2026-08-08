export default function SiteSummaryPanel({ siteSummary } = {}) {
  const sites = Array.isArray(siteSummary) ? siteSummary : [];

  return (
    <section className="dashboard-section site-summary-section" aria-label="Site Summary">
      <h3 className="section-title">Site Summary</h3>
      {sites.length === 0 ? (
        <p className="empty-state-message">No sites available.</p>
      ) : (
        <table className="site-summary-table">
          <thead>
            <tr>
              <th>Site Code</th>
              <th>Site Name</th>
              <th>Robots</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((site) => (
              <tr key={site.site_id}>
                <td>{site.site_code}</td>
                <td>{site.site_name}</td>
                <td>{site.robot_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
