import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Robots from "../pages/Robots.jsx";

const api = vi.hoisted(() => ({
  getRobots: vi.fn(),
  getRobotHealth: vi.fn(),
  updateRobotStatus: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { email: "viewer@example.com", role: "viewer" } }));

vi.mock("../services/api.js", () => api);
vi.mock("../auth/AuthContext.jsx", () => ({ useAuth: () => auth }));

const robot = {
  id: "robot-1",
  robot_code: "RBT-001",
  name: "Warehouse Scout",
  serial_number: "SN-001",
  site_id: "site-1",
  model_id: "model-1",
  status: "active",
  installed_at: "2025-01-01T00:00:00Z",
};

function renderPage(role = "viewer") {
  auth.user = { email: `${role}@example.com`, role };
  return render(<Robots />);
}

describe("Robots page", () => {
  beforeEach(() => {
    api.getRobots.mockReset();
    api.getRobotHealth.mockReset();
    api.updateRobotStatus.mockReset();
    api.getRobotHealth.mockResolvedValue({ robots: [] });
    auth.user = { email: "viewer@example.com", role: "viewer" };
  });

  it("renders real fetched robot rows", async () => {
    api.getRobots.mockResolvedValue([robot]);
    renderPage();
    expect(await screen.findByText("Warehouse Scout")).toBeInTheDocument();
    expect(screen.getByText("RBT-001")).toBeInTheDocument();
    expect(screen.getByText("SN-001")).toBeInTheDocument();
    expect(screen.getByText("site-1")).toBeInTheDocument();
    expect(screen.getByText("model-1")).toBeInTheDocument();
    expect(screen.getByText("1 robot")).toBeInTheDocument();
  });

  it("renders aggregate telemetry health without per-robot requests", async () => {
    api.getRobots.mockResolvedValue([robot]);
    api.getRobotHealth.mockResolvedValue({
      robots: [{ robot_id: "robot-1", health_state: "warning", reason_codes: ["battery_low"] }],
    });
    renderPage();
    expect(await screen.findByText("warning")).toBeInTheDocument();
    expect(screen.getByText("battery_low")).toBeInTheDocument();
    expect(api.getRobotHealth).toHaveBeenCalledTimes(1);
  });

  it("renders loading state", () => {
    api.getRobots.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Loading robots...")).toBeInTheDocument();
  });

  it("renders a retryable load error", async () => {
    api.getRobots.mockRejectedValueOnce(new Error("network failure")).mockResolvedValueOnce([]);
    renderPage();
    expect(await screen.findByText("Unable to load robots. Please try again.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(api.getRobots).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("No robots found.")).toBeInTheDocument();
  });

  it("renders the empty state without a create action", async () => {
    api.getRobots.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No robots found.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create robot/i })).not.toBeInTheDocument();
  });

  it("does not show mutation controls to viewers", async () => {
    api.getRobots.mockResolvedValue([robot]);
    renderPage("viewer");
    await screen.findByText("Warehouse Scout");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it.each(["operator", "admin"])('shows mutation controls to %s', async (role) => {
    api.getRobots.mockResolvedValue([robot]);
    renderPage(role);
    expect(await screen.findByRole("combobox")).toBeInTheDocument();
  });

  it("offers only operational status options", async () => {
    api.getRobots.mockResolvedValue([robot]);
    renderPage("operator");
    const select = await screen.findByRole("combobox");
    expect(within(select).getAllByRole("option").map((option) => option.value)).toEqual([
      "active", "idle", "maintenance", "offline",
    ]);
  });

  it("displays decommissioned robots without a status control", async () => {
    api.getRobots.mockResolvedValue([{ ...robot, status: "decommissioned" }]);
    renderPage("admin");
    expect(await screen.findByText("decommissioned")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("updates status using the returned robot", async () => {
    api.getRobots.mockResolvedValue([robot]);
    api.updateRobotStatus.mockResolvedValue({ ...robot, status: "maintenance" });
    renderPage("operator");
    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "maintenance" } });
    expect(api.updateRobotStatus).toHaveBeenCalledWith("robot-1", "maintenance");
    await waitFor(() => expect(screen.getByText("maintenance")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue("maintenance"));
  });

  it("shows permission feedback and keeps page data after a 403", async () => {
    api.getRobots.mockResolvedValue([robot]);
    api.updateRobotStatus.mockRejectedValue({ status: 403 });
    renderPage("operator");
    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "offline" } });
    expect(await screen.findByText("You do not have permission to change robot status.")).toBeInTheDocument();
    expect(select).toHaveValue("active");
    expect(screen.getByText("Warehouse Scout")).toBeInTheDocument();
  });

  it("restores the previous status after another mutation failure", async () => {
    api.getRobots.mockResolvedValue([robot]);
    api.updateRobotStatus.mockRejectedValue({ status: 500 });
    renderPage("admin");
    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "idle" } });
    await waitFor(() => expect(select).toHaveValue("active"));
    expect(screen.getByText("Unable to update robot status. Please try again.")).toBeInTheDocument();
  });

  it("prevents duplicate updates while a mutation is pending", async () => {
    api.getRobots.mockResolvedValue([robot]);
    api.updateRobotStatus.mockReturnValue(new Promise(() => {}));
    renderPage("operator");
    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "idle" } });
    fireEvent.change(select, { target: { value: "offline" } });
    expect(api.updateRobotStatus).toHaveBeenCalledTimes(1);
    expect(select).toBeDisabled();
  });
});