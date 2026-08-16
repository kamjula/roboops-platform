import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MaintenancePanel from "../components/dashboard/MaintenancePanel.jsx";

describe("MaintenancePanel", () => {
  it("renders all five real maintenance counts", () => {
    render(
      <MaintenancePanel
        maintenanceSummary={{
          scheduled_count: 3,
          in_progress_count: 1,
          due_count: 4,
          overdue_count: 2,
          completed_count: 9,
          as_of: "2026-08-08T00:00:00Z",
        }}
      />
    );
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Due")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
  });

  it("renders real as_of value", () => {
    const asOf = "2026-08-08T00:00:00Z";
    render(
      <MaintenancePanel
        maintenanceSummary={{
          scheduled_count: 3,
          in_progress_count: 1,
          due_count: 4,
          overdue_count: 2,
          completed_count: 9,
          as_of: asOf,
        }}
      />
    );
    const expectedLabel = new Date(asOf).toLocaleString();
    expect(screen.getByText(`Updated as of ${expectedLabel}`)).toBeInTheDocument();
  });

  it("handles zero values correctly", () => {
    render(
      <MaintenancePanel
        maintenanceSummary={{
          scheduled_count: 0,
          in_progress_count: 0,
          due_count: 0,
          overdue_count: 0,
          completed_count: 0,
          as_of: null,
        }}
      />
    );
    expect(screen.getAllByText("0")).toHaveLength(5);
  });
});
