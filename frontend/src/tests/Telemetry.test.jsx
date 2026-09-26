import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Telemetry from "../pages/Telemetry.jsx";
import { getRobots, getTelemetryTrends } from "../services/api.js";

vi.mock("../services/api.js", () => ({ getRobots: vi.fn(), getTelemetryTrends: vi.fn() }));
vi.mock("../components/layout/Header.jsx", () => ({ default: ({ title }) => <header>{title}</header> }));
vi.mock("../components/analytics/TrendPanel.jsx", () => ({ default: ({ trends }) => <div>Chart series: {trends.series.length}</div> }));

const response = {
  as_of: "2026-09-26T12:00:00Z",
  window_start: "2026-09-25T12:00:00Z",
  total_readings: 12,
  series_count: 1,
  points_truncated: true,
  series: [{
    sensor_id: "sensor-1", robot_id: "11111111-1111-1111-1111-111111111111", robot_code: "RB-001",
    sensor_type: "temperature", unit: "C", reading_count: 12,
    min_value: 20.1, avg_value: 25.253, max_value: 30.7,
    latest_recorded_at: "2026-09-26T12:00:00Z", points: [],
  }],
};

describe("Telemetry explorer", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getRobots.mockResolvedValue([{ id: response.series[0].robot_id, robot_code: "RB-001" }]);
    getTelemetryTrends.mockResolvedValue(response);
  });

  it("shows persisted summary statistics and filters the backend request", async () => {
    render(<Telemetry />);
    expect(await screen.findByText("12 readings across 1 sensor series")).toBeInTheDocument();
    expect(screen.getByText("20.10 C")).toBeInTheDocument();
    expect(screen.getByText("25.25 C")).toBeInTheDocument();
    expect(screen.getByText("30.70 C")).toBeInTheDocument();
    expect(screen.getByText(/table statistics cover all readings/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("option", { name: "RB-001" })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Robot"), { target: { value: response.series[0].robot_id } });
    fireEvent.change(screen.getByLabelText("Time window"), { target: { value: "72" } });
    await waitFor(() => expect(getTelemetryTrends).toHaveBeenLastCalledWith({ lookbackHours: 72, robotId: response.series[0].robot_id }));
  });

  it("ignores a stale response and handles empty readings", async () => {
    let resolveOld;
    getTelemetryTrends.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }))
      .mockResolvedValue({ ...response, total_readings: 0, series_count: 0, series: [] });
    render(<Telemetry />);
    await waitFor(() => expect(resolveOld).toBeTypeOf("function"));
    fireEvent.change(screen.getByLabelText("Time window"), { target: { value: "72" } });
    expect(await screen.findByText("No sensor readings in this window.")).toBeInTheDocument();
    resolveOld(response);
    await waitFor(() => expect(screen.getByText("0 readings across 0 sensor series")).toBeInTheDocument());
  });
});
