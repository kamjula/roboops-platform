import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Analytics from "../pages/Analytics.jsx";
import { AuthProvider } from "../auth/AuthContext.jsx";
import * as api from "../services/api.js";

vi.mock("recharts", () => ({
  CartesianGrid: () => null,
  Line: () => null,
  LineChart: ({ children }) => children,
  ResponsiveContainer: ({ children }) => children,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

vi.mock("../services/api.js", () => ({
  getCurrentUser: vi.fn().mockResolvedValue({ email: "viewer@example.com", role: "viewer" }),
  getStatisticalAnomalies: vi.fn(),
  getTelemetryAnomalies: vi.fn(),
  getTelemetryConditions: vi.fn(),
  getTelemetryTrends: vi.fn(),
}));

const deterministic = {
  lookback_hours: 24,
  total_readings: 120,
  severity_counts: { warning: 2, critical: 1 },
  anomaly_events: [{}, {}, {}],
  anomaly_events_truncated: false,
};

const statistical = {
  baseline_hours: 24,
  status_counts: { normal: 4, warning: 2 },
  results: [],
};

const trends = {
  total_readings: 120,
  points_truncated: false,
  series: [{
    sensor_id: "sensor-1",
    robot_code: "RB-001",
    sensor_type: "temperature",
    unit: "C",
    latest_value: 42.5,
    points: [{ recorded_at: "2026-09-22T12:00:00Z", value: 42.5 }],
  }],
};

const conditions = {
  condition_model_version: "rms-z-v1",
  robots: [
    { robot_id: "12345678-aaaa-bbbb-cccc-123456789012", status: "warning", score: 2.4, baseline_row_count: 20, reason: "elevated_signal" },
    { robot_id: "87654321-aaaa-bbbb-cccc-123456789012", status: "normal", score: 0.7, baseline_row_count: 20, reason: "within_baseline" },
  ],
};

function arrangeSuccessfulResponses() {
  api.getTelemetryAnomalies.mockResolvedValue(deterministic);
  api.getStatisticalAnomalies.mockResolvedValue(statistical);
  api.getTelemetryTrends.mockResolvedValue(trends);
  api.getTelemetryConditions.mockResolvedValue(conditions);
}

describe("Analytics page", () => {
  it("renders real telemetry evidence and the non-predictive limitation", async () => {
    arrangeSuccessfulResponses();
    sessionStorage.setItem("roboops.access_token", "test-token");
    render(
      <MemoryRouter>
        <AuthProvider><Analytics /></AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("Readings evaluated")).toBeInTheDocument());
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("RB-001")).toBeInTheDocument();
    expect(screen.getByText("rms-z-v1")).toBeInTheDocument();
    expect(screen.getByText(/not failure probabilities/i)).toBeInTheDocument();
    expect(screen.getByText("12345678")).toBeInTheDocument();
  });

  it("refetches every analytics endpoint when the analysis window changes", async () => {
    arrangeSuccessfulResponses();
    sessionStorage.setItem("roboops.access_token", "test-token");
    render(
      <MemoryRouter>
        <AuthProvider><Analytics /></AuthProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(api.getTelemetryAnomalies).toHaveBeenCalledWith({ lookbackHours: 24 }));

    fireEvent.change(screen.getByLabelText("Analysis window"), { target: { value: "72" } });

    await waitFor(() => expect(api.getTelemetryAnomalies).toHaveBeenLastCalledWith({ lookbackHours: 72 }));
    expect(api.getStatisticalAnomalies).toHaveBeenLastCalledWith({ baselineHours: 72 });
    expect(api.getTelemetryTrends).toHaveBeenLastCalledWith({ lookbackHours: 72 });
    expect(api.getTelemetryConditions).toHaveBeenLastCalledWith({ lookbackHours: 72 });
  });
});
