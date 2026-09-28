import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Tasks from "../pages/Tasks.jsx";
import AIAssistant from "../pages/AIAssistant.jsx";
import Settings from "../pages/Settings.jsx";
import * as api from "../services/api.js";

vi.mock("../services/api.js", () => ({ getAlerts: vi.fn(), getMaintenanceWorkspace: vi.fn(), getRobotHealth: vi.fn() }));
vi.mock("../auth/AuthContext.jsx", () => ({ useAuth: () => ({ user: { email: "demo@roboops.example", role: "viewer" } }) }));
vi.mock("../components/layout/Header.jsx", () => ({ default: ({ title }) => <h1>{title}</h1> }));

beforeEach(() => {
  vi.clearAllMocks();
  api.getAlerts.mockResolvedValue([{ id: "a1", robot_code: "RBT-003", severity: "warning", message: "Temperature above threshold", triggered_at: "2026-09-28T00:00:00Z" }]);
  api.getMaintenanceWorkspace.mockResolvedValue({ schedule_total: 1, schedules: [{ id: "s1", robot_code: "RBT-001", maintenance_type: "inspection", scheduled_for: "2026-01-15T00:00:00Z", status: "scheduled" }] });
  api.getRobotHealth.mockResolvedValue({ robots: [{ robot_id: "r3", robot_code: "RBT-003", health_state: "warning", reason_codes: ["temperature_high"] }] });
});

describe("operational workspaces", () => {
  it("links a read-only action queue to its underlying alert and maintenance records", async () => {
    render(<MemoryRouter><Tasks /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText("Temperature above threshold")).toBeInTheDocument());
    expect(screen.getByText(/not create or complete task records/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Review alerts/ })).toHaveAttribute("href", "/alerts");
    expect(screen.getByRole("link", { name: /Review maintenance/ })).toHaveAttribute("href", "/maintenance");
  });

  it("answers guided questions from returned evidence and discloses no LLM", async () => {
    render(<MemoryRouter><AIAssistant /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/1 of 1 robots/)).toBeInTheDocument());
    expect(screen.getByText(/no LLM is connected/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "What alerts are open?" }));
    expect(screen.getByText("Temperature above threshold")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "What maintenance is scheduled?" }));
    expect(screen.getByText(/fixed historical dates/)).toBeInTheDocument();
  });

  it("shows the real session role and synthetic demo label", () => {
    render(<Settings />);
    expect(screen.getByText("demo@roboops.example")).toBeInTheDocument();
    expect(screen.getByText("viewer")).toBeInTheDocument();
    expect(screen.getByText("Synthetic demonstration fleet")).toBeInTheDocument();
  });
});
