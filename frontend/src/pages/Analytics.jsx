import { useState } from "react";
import Header from "../components/layout/Header.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import AnalyticsSummary from "../components/analytics/AnalyticsSummary.jsx";
import AnomalyPanel from "../components/analytics/AnomalyPanel.jsx";
import TrendPanel from "../components/analytics/TrendPanel.jsx";
import ConditionTable from "../components/analytics/ConditionTable.jsx";
import useAnalyticsData from "../hooks/useAnalyticsData.js";

const LOOKBACK_OPTIONS = [24, 72, 168];

export default function Analytics() {
  const [lookbackHours, setLookbackHours] = useState(24);
  const { data, error, loading, refetch } = useAnalyticsData(lookbackHours);

  return (
    <section className="page analytics-page">
      <Header title="Analytics" />
      <div className="analytics-heading">
        <div>
          <div className="eyebrow">Evidence from persisted telemetry</div>
          <h1>Fleet analytics</h1>
          <p>Inspect bounded anomaly signals, telemetry trends, and honest condition scores.</p>
        </div>
        <label className="analytics-lookback">
          Analysis window
          <select value={lookbackHours} onChange={(event) => setLookbackHours(Number(event.target.value))}>
            {LOOKBACK_OPTIONS.map((hours) => <option key={hours} value={hours}>Last {hours} hours</option>)}
          </select>
        </label>
      </div>

      {loading ? <LoadingState label="Loading fleet analytics..." /> : null}
      {!loading && error ? <ErrorState message={error.message} onRetry={refetch} /> : null}
      {!loading && !error ? (
        <>
          <AnalyticsSummary
            deterministic={data.deterministic}
            statistical={data.statistical}
            conditions={data.conditions}
          />
          <AnomalyPanel deterministic={data.deterministic} statistical={data.statistical} />
          <TrendPanel trends={data.trends} lookbackHours={lookbackHours} />
          <ConditionTable conditions={data.conditions} trends={data.trends} />
        </>
      ) : null}
    </section>
  );
}
