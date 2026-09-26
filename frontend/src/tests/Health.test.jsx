import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Health from "../pages/Health.jsx";
import { getRobotHealth } from "../services/api.js";

vi.mock("../services/api.js", () => ({ getRobotHealth: vi.fn() }));
vi.mock("../components/layout/Header.jsx", () => ({ default: ({ title }) => <header>{title}</header> }));

const response = {
  as_of: "2026-09-26T12:00:00Z",
  freshness_threshold_seconds: 900,
  robots: [
    { robot_id: "1", robot_code: "RB-001", robot_name: "Picker", operational_status: "active", health_state: "healthy", reason_codes: [], battery: { value: 84, unit: "%", freshness: "fresh", state: "healthy" }, temperature: null },
    { robot_id: "2", robot_code: "RB-002", robot_name: "Carrier", operational_status: "offline", health_state: "critical", reason_codes: ["robot_offline"], battery: null, temperature: { value: 81.3, unit: "C", freshness: "stale", state: "unknown" } },
  ],
};

describe("Health page", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows real health states, sensor freshness, and missing readings without predicting failure", async () => {
    getRobotHealth.mockResolvedValue(response);
    render(<Health />);
    expect(await screen.findByText("RB-002")).toBeInTheDocument();
    expect(screen.getByText("84.00 % · fresh · healthy")).toBeInTheDocument();
    expect(screen.getByText("81.30 C · stale · unknown")).toBeInTheDocument();
    expect(screen.getAllByText("No reading available")).toHaveLength(2);
    expect(screen.getByText("robot offline")).toBeInTheDocument();
    expect(screen.getByText(/not failure predictions/i)).toBeInTheDocument();
    expect(screen.getByText("Freshness threshold: 900 seconds")).toBeInTheDocument();
  });

  it("distinguishes an empty fleet from a failed health request", async () => {
    getRobotHealth.mockResolvedValue({ ...response, robots: [] });
    const { unmount } = render(<Health />);
    expect(await screen.findByText("No robots found in the fleet.")).toBeInTheDocument();
    unmount();
    getRobotHealth.mockRejectedValue(new Error("network"));
    render(<Health />);
    await waitFor(() => expect(screen.getByText("Unable to load fleet health.")).toBeInTheDocument());
  });
});
