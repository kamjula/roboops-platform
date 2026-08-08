import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RobotStatusChart from "../components/dashboard/RobotStatusChart.jsx";

const robotStatus = {
  total_robots: 12,
  active: 8,
  idle: 2,
  maintenance: 1,
  offline: 1,
  decommissioned: 0,
};

describe("RobotStatusChart", () => {
  it("renders all five status categories with real counts", () => {
    render(<RobotStatusChart robotStatus={robotStatus} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Idle")).toBeInTheDocument();
    expect(screen.getByText("Maintenance")).toBeInTheDocument();
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByText("Decommissioned")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("handles all-zero data safely without crashing", () => {
    const zeroStatus = {
      total_robots: 0,
      active: 0,
      idle: 0,
      maintenance: 0,
      offline: 0,
      decommissioned: 0,
    };
    render(<RobotStatusChart robotStatus={zeroStatus} />);
    expect(screen.getByText("No robot status data available.")).toBeInTheDocument();
  });

  it("renders nothing when robotStatus is not provided", () => {
    const { container } = render(<RobotStatusChart robotStatus={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
