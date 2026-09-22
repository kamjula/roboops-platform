import { useCallback, useEffect, useState } from "react";
import {
  getStatisticalAnomalies,
  getTelemetryAnomalies,
  getTelemetryConditions,
  getTelemetryTrends,
} from "../services/api.js";

const EMPTY_DATA = {
  deterministic: null,
  statistical: null,
  trends: null,
  conditions: null,
};

export default function useAnalyticsData(lookbackHours) {
  const [data, setData] = useState(EMPTY_DATA);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [deterministic, statistical, trends, conditions] = await Promise.all([
        getTelemetryAnomalies({ lookbackHours }),
        getStatisticalAnomalies({ baselineHours: lookbackHours }),
        getTelemetryTrends({ lookbackHours }),
        getTelemetryConditions({ lookbackHours }),
      ]);
      setData({ deterministic, statistical, trends, conditions });
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [lookbackHours]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, error, loading, refetch: fetchData };
}
