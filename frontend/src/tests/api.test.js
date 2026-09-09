import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  ACCESS_TOKEN_KEY,
  getCurrentUser,
  getDashboardSummary,
  getRobotStatus,
  getSiteSummary,
  getMaintenanceSummary,
  getLatestAlerts,
  getHealthSummary,
  getRobots,
  login,
  updateRobotStatus,
} from "../services/api.js";

function mockFetchOnce(body) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => body,
  });
}

describe("dashboard api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls the summary endpoint", async () => {
    mockFetchOnce({ total_robots: 1 });
    await getDashboardSummary();
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/summary");
  });

  it("calls the robots endpoint with pagination parameters", async () => {
    mockFetchOnce([]);
    await getRobots({ skip: 10, limit: 25 });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/robots");
    expect(calledUrl).toContain("skip=10");
    expect(calledUrl).toContain("limit=25");
  });

  it("updates a robot operational status with JSON", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    mockFetchOnce({ id: "robot-1", status: "maintenance" });
    await updateRobotStatus("robot-1", "maintenance");
    const [calledUrl, options] = global.fetch.mock.calls[0];
    expect(calledUrl.toString()).toContain("/api/v1/robots/robot-1/status");
    expect(options.method).toBe("PATCH");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(options.headers.Authorization).toBe("Bearer stored-token");
    expect(options.body).toBe(JSON.stringify({ status: "maintenance" }));
  });

  it("submits login credentials as a form with username mapped from email", async () => {
    mockFetchOnce({ access_token: "token" });
    await login("operator@example.com", "secret");
    const [, options] = global.fetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
    expect(options.body.toString()).toBe("username=operator%40example.com&password=secret");
  });

  it("injects the current bearer token and supports the current-user endpoint", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    mockFetchOnce({ email: "viewer@example.com", role: "viewer" });
    await getCurrentUser();
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer stored-token");
  });

  it("omits authorization when no token is stored", async () => {
    mockFetchOnce({ total_robots: 0 });
    await getDashboardSummary();
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("calls the robot-status endpoint", async () => {
    mockFetchOnce({});
    await getRobotStatus();
    expect(global.fetch.mock.calls[0][0].toString()).toContain("/api/v1/dashboard/robot-status");
  });

  it("calls the site-summary endpoint", async () => {
    mockFetchOnce([]);
    await getSiteSummary();
    expect(global.fetch.mock.calls[0][0].toString()).toContain("/api/v1/dashboard/site-summary");
  });

  it("calls the maintenance-summary endpoint", async () => {
    mockFetchOnce({});
    await getMaintenanceSummary();
    expect(global.fetch.mock.calls[0][0].toString()).toContain("/api/v1/dashboard/maintenance-summary");
  });

  it("calls the latest-alerts endpoint with a limit query param", async () => {
    mockFetchOnce([]);
    await getLatestAlerts({ limit: 5 });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/latest-alerts");
    expect(calledUrl).toContain("limit=5");
  });

  it("calls the health-summary endpoint", async () => {
    mockFetchOnce({});
    await getHealthSummary();
    expect(global.fetch.mock.calls[0][0].toString()).toContain("/api/v1/dashboard/health-summary");
  });

  it("throws a descriptive error on non-2xx responses", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "Server Error" });
    await expect(getDashboardSummary()).rejects.toThrow(/500/);
  });

  it("preserves 401 and 403 statuses on API errors", async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 401, statusText: "Unauthorized" })
      .mockResolvedValueOnce({ ok: false, status: 403, statusText: "Forbidden" });
    await expect(getDashboardSummary()).rejects.toMatchObject({ status: 401 });
    await expect(getDashboardSummary()).rejects.toMatchObject({ status: 403 });
  });

  it("does not emit an unauthorized event for a 403 response", async () => {
    const unauthorized = vi.fn();
    window.addEventListener("roboops:unauthorized", unauthorized);
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 403, statusText: "Forbidden" });
    await expect(getDashboardSummary()).rejects.toMatchObject({ status: 403 });
    expect(unauthorized).not.toHaveBeenCalled();
    window.removeEventListener("roboops:unauthorized", unauthorized);
  });

  it("rejects with a descriptive timeout error when a request exceeds the timeout", async () => {
    vi.useFakeTimers();
    global.fetch = vi.fn((url, { signal } = {}) => new Promise((_, reject) => {
      signal.addEventListener("abort", () => {
        const abortError = new Error("The operation was aborted");
        abortError.name = "AbortError";
        reject(abortError);
      });
    }));

    // Attach the rejection assertion immediately so the promise always has a
    // handler before the fake timer advances and triggers the abort, avoiding
    // a spurious unhandled-rejection warning.
    const pending = getDashboardSummary();
    const assertion = expect(pending).rejects.toThrow(/timed out/i);

    await vi.advanceTimersByTimeAsync(8000);
    await assertion;
  });
});
