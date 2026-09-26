import { useCallback, useEffect, useRef, useState } from "react";
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
  const requestId = useRef(0);

  const fetchData = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const [deterministic, statistical, trends, conditions] = await Promise.all([
        getTelemetryAnomalies({ lookbackHours }),
        getStatisticalAnomalies({ baselineHours: lookbackHours }),
        getTelemetryTrends({ lookbackHours }),
        getTelemetryConditions({ lookbackHours }),
      ]);
      if (currentRequest === requestId.current) {
        setData({ deterministic, statistical, trends, conditions });
      }
    } catch (requestError) {
      if (currentRequest === requestId.current) setError(requestError);
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [lookbackHours]);

  useEffect(() => {
    fetchData();
    return () => { requestId.current += 1; };
  }, [fetchData]);

  return { data, error, loading, refetch: fetchData };
}
