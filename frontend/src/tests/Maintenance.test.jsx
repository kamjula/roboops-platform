import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Maintenance from "../pages/Maintenance.jsx";
import * as api from "../services/api.js";

vi.mock("../services/api.js", () => ({ getMaintenanceWorkspace: vi.fn() }));
vi.mock("../components/layout/Header.jsx", () => ({ default: ({ title }) => <h1>{title}</h1> }));

beforeEach(() => vi.clearAllMocks());

describe("Maintenance", () => {
  it("shows persisted schedule and service with synthetic data disclosure", async () => {
    api.getMaintenanceWorkspace.mockResolvedValue({
      schedule_total: 2, record_total: 1,
      schedules: [{ id: "s1", robot_code: "RB-1", robot_name: "Scout", scheduled_for: "2026-01-15T00:00:00Z", maintenance_type: "inspection", status: "scheduled", notes: null }],
      records: [{ id: "r1", robot_code: "RB-1", robot_name: "Scout", performed_at: "2025-12-01T00:00:00Z", maintenance_type: "repair", technician_name: "Alex", description: null, cost_usd: 125 }],
    });
    render(<Maintenance />);
    await waitFor(() => expect(screen.getAllByText("RB-1", { selector: "strong" })).toHaveLength(2));
    expect(screen.getByText(/synthetic, fixed-date seed data/)).toBeInTheDocument();
    expect(screen.getByText(/Showing first 1 of 2 schedules/)).toBeInTheDocument();
    expect(screen.getByText("Alex")).toBeInTheDocument();
    expect(screen.getByText("$125.00")).toBeInTheDocument();
  });
});
