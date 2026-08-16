import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RecentAlerts from "../components/dashboard/RecentAlerts.jsx";

const alerts = [
  {
    id: 1,
    robot_code: "RBT-001",
    robot_name: "Scout One",
    severity: "critical",
    alert_type: "battery_low",
    message: "Battery critically low",
    created_at: "2026-08-08T10:00:00Z",
  },
  {
    id: 2,
    robot_code: "RBT-002",
    robot_name: "Scout Two",
    severity: "warning",
    alert_type: "sensor_fault",
    message: "Sensor reading unstable",
    created_at: "2026-08-08T09:00:00Z",
  },
];

describe("RecentAlerts", () => {
  it("renders supplied alerts with robot details", () => {
    render(<RecentAlerts alerts={alerts} />);
    expect(screen.getByText("RBT-001")).toBeInTheDocument();
    expect(screen.getByText("Scout One")).toBeInTheDocument();
    expect(screen.getByText("Battery critically low")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("RBT-002")).toBeInTheDocument();
    expect(screen.getByText("Warning")).toBeInTheDocument();
  });

  it("preserves the supplied ordering without re-sorting", () => {
    render(<RecentAlerts alerts={alerts} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("RBT-001");
    expect(items[1]).toHaveTextContent("RBT-002");
  });

  it("handles an empty alerts array cleanly", () => {
    render(<RecentAlerts alerts={[]} />);
    expect(screen.getByText("No recent alerts.")).toBeInTheDocument();
  });
});
