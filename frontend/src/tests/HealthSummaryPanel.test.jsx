import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HealthSummaryPanel from "../components/dashboard/HealthSummaryPanel.jsx";

const baseHealthSummary = {
  average_health_value: null,
  health_metric_available: false,
  robot_status_counts: { active: 8, idle: 2, maintenance: 1, offline: 1, decommissioned: 0 },
  maintenance_due_count: 4,
  maintenance_overdue_count: 1,
};

describe("HealthSummaryPanel", () => {
  it("explicitly handles unavailable aggregate health metric", () => {
    render(<HealthSummaryPanel healthSummary={baseHealthSummary} />);
    expect(
      screen.getByText("Aggregate health metric is not currently available.")
    ).toBeInTheDocument();
  });

  it("renders real robot status counts", () => {
    render(<HealthSummaryPanel healthSummary={baseHealthSummary} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Idle")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders maintenance due/overdue values", () => {
    render(<HealthSummaryPanel healthSummary={baseHealthSummary} />);
    expect(screen.getByText("Maintenance Due")).toBeInTheDocument();
    expect(screen.getByText("Maintenance Overdue")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("handles missing data safely", () => {
    render(<HealthSummaryPanel healthSummary={null} />);
    expect(screen.getByText("Health data unavailable.")).toBeInTheDocument();
  });

    it("renders all-zero counts without treating them as missing", () => {
          const zeroHealthSummary = {
                  average_health_value: null,
                  health_metric_available: false,
                  robot_status_counts: { active: 0, idle: 0, maintenance: 0, offline: 0, decommissioned: 0 },
                  maintenance_due_count: 0,
                  maintenance_overdue_count: 0,
          };
          render(<HealthSummaryPanel healthSummary={zeroHealthSummary} />);
          expect(
                  screen.getByText("Aggregate health metric is not currently available.")
                ).toBeInTheDocument();
          expect(screen.getByText("Active")).toBeInTheDocument();
          expect(screen.getByText("Maintenance Due")).toBeInTheDocument();
          expect(screen.getByText("Maintenance Overdue")).toBeInTheDocument();
          expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(7);
    });
});
