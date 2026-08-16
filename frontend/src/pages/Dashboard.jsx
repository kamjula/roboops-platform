import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import SummaryCards from "../components/dashboard/SummaryCards.jsx";
import RobotStatusChart from "../components/dashboard/RobotStatusChart.jsx";
import RecentAlerts from "../components/dashboard/RecentAlerts.jsx";
import HealthSummaryPanel from "../components/dashboard/HealthSummaryPanel.jsx";
import MaintenancePanel from "../components/dashboard/MaintenancePanel.jsx";
import SiteSummaryPanel from "../components/dashboard/SiteSummaryPanel.jsx";
import useDashboardData from "../hooks/useDashboardData.js";

export default function Dashboard() {
  const { data, loading, error, refetch } = useDashboardData();

  return (
    <section className="page dashboard-page">
      <Header title="Dashboard" />
      {loading ? <LoadingState label="Loading fleet dashboard..." /> : null}
      {!loading && error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : null}
      {!loading && !error ? (
        <>
          <SummaryCards summary={data.summary} maintenanceSummary={data.maintenanceSummary} />
          <div className="dashboard-grid">
            <RobotStatusChart robotStatus={data.robotStatus} />
            <HealthSummaryPanel healthSummary={data.healthSummary} />
            <RecentAlerts alerts={data.latestAlerts} />
            <MaintenancePanel maintenanceSummary={data.maintenanceSummary} />
            <SiteSummaryPanel siteSummary={data.siteSummary} />
          </div>
        </>
      ) : null}
    </section>
  );
}
