import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Alerts from "../pages/Alerts.jsx";

const api = vi.hoisted(() => ({ getAlerts: vi.fn(), resolveAlert: vi.fn() }));
const auth = vi.hoisted(() => ({ user: { email: "viewer@example.com", role: "viewer" } }));

vi.mock("../services/api.js", () => api);
vi.mock("../auth/AuthContext.jsx", () => ({ useAuth: () => auth }));

const alert = {
  id: "alert-1",
  robot_id: "robot-1",
  robot_code: "RBT-001",
  robot_name: "Warehouse Scout",
  severity: "critical",
  alert_type: "temperature_anomaly",
  message: "Temperature condition exceeded the configured threshold.",
  triggered_at: "2026-09-18T12:00:00Z",
  resolved_at: null,
};

function renderPage(role = "viewer") {
  auth.user = { email: `${role}@example.com`, role };
  return render(<Alerts />);
}

describe("Alerts page", () => {
  beforeEach(() => {
    api.getAlerts.mockReset();
    api.resolveAlert.mockReset();
    api.getAlerts.mockResolvedValue([alert]);
  });

  it("renders persisted alert data and hides mutations from viewers", async () => {
    renderPage();
    expect(await screen.findByText("RBT-001")).toBeInTheDocument();
    expect(screen.getByText("Warehouse Scout")).toBeInTheDocument();
    expect(screen.getByText("temperature_anomaly")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolve" })).not.toBeInTheDocument();
  });

  it.each(["operator", "admin"])("allows %s to resolve an open alert", async (role) => {
    api.resolveAlert.mockResolvedValue({ ...alert, resolved_at: "2026-09-18T12:30:00Z" });
    renderPage(role);
    fireEvent.click(await screen.findByRole("button", { name: "Resolve" }));
    expect(api.resolveAlert).toHaveBeenCalledWith("alert-1");
    await waitFor(() => expect(screen.queryByText("RBT-001")).not.toBeInTheDocument());
    expect(screen.getByText("No alerts match these filters.")).toBeInTheDocument();
  });

  it("reloads when filters change", async () => {
    renderPage();
    await screen.findByText("RBT-001");
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "resolved" } });
    await waitFor(() => expect(api.getAlerts).toHaveBeenLastCalledWith({ status: "resolved", severity: undefined }));
    fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "warning" } });
    await waitFor(() => expect(api.getAlerts).toHaveBeenLastCalledWith({ status: "resolved", severity: "warning" }));
  });

  it("keeps the alert visible and reports mutation failure", async () => {
    api.resolveAlert.mockRejectedValue({ status: 500 });
    renderPage("operator");
    fireEvent.click(await screen.findByRole("button", { name: "Resolve" }));
    expect(await screen.findByText("Unable to resolve the alert. Please try again.")).toBeInTheDocument();
    expect(screen.getByText("RBT-001")).toBeInTheDocument();
  });

  it("renders a retryable load error", async () => {
    api.getAlerts.mockRejectedValueOnce(new Error("network")).mockResolvedValueOnce([]);
    renderPage();
    expect(await screen.findByText("Unable to load alerts. Please try again.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No alerts match these filters.")).toBeInTheDocument();
  });
});
