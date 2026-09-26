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
  getStatisticalAnomalies,
  getTelemetryAnomalies,
  getTelemetryConditions,
  getTelemetryTrends,
  login,
  loginDemo,
  logout,
  syncConditionAlerts,
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

  it("calls the fleet telemetry-condition endpoint once", async () => {
    mockFetchOnce({ robots: [] });
    await getTelemetryConditions({ lookbackHours: 48 });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/telemetry-conditions");
    expect(calledUrl).toContain("lookback_hours=48");
  });

  it("calls the deterministic anomaly endpoint with a bounded lookback", async () => {
    mockFetchOnce({ anomaly_events: [] });
    await getTelemetryAnomalies({ lookbackHours: 72 });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/telemetry-anomalies");
    expect(calledUrl).toContain("lookback_hours=72");
  });

  it("calls the statistical anomaly endpoint with baseline and robot filters", async () => {
    mockFetchOnce({ results: [] });
    await getStatisticalAnomalies({ baselineHours: 168, robotId: "robot-1" });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/statistical-anomalies");
    expect(calledUrl).toContain("baseline_hours=168");
    expect(calledUrl).toContain("robot_id=robot-1");
  });

  it("calls the telemetry trend endpoint with the selected window", async () => {
    mockFetchOnce({ series: [] });
    await getTelemetryTrends({ lookbackHours: 24 });
    const calledUrl = global.fetch.mock.calls[0][0].toString();
    expect(calledUrl).toContain("/api/v1/dashboard/telemetry-trends");
    expect(calledUrl).toContain("lookback_hours=24");
  });

  it("posts the condition-alert sync with an explicit lookback", async () => {
    mockFetchOnce({ evaluated: 0 });
    await syncConditionAlerts({ lookbackHours: 72 });
    const [calledUrl, options] = global.fetch.mock.calls[0];
    expect(calledUrl.toString()).toContain("/api/v1/alerts/sync-conditions");
    expect(calledUrl.toString()).toContain("lookback_hours=72");
    expect(options.method).toBe("POST");
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

  it("opens a public demo session with a bounded cold-start timeout", async () => {
    mockFetchOnce({ access_token: "demo-token" });
    await loginDemo();
    const [url, options] = global.fetch.mock.calls[0];
    expect(url.toString()).toContain("/api/v1/auth/demo");
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("injects the current bearer token and supports the current-user endpoint", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    mockFetchOnce({ email: "viewer@example.com", role: "viewer" });
    await getCurrentUser();
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer stored-token");
  });

  it("posts logout with the bearer token and accepts an empty 204 response", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      statusText: "No Content",
    });

    await expect(logout()).resolves.toBeNull();
    const [calledUrl, options] = global.fetch.mock.calls[0];
    expect(calledUrl.toString()).toContain("/api/v1/auth/logout");
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBe("Bearer stored-token");
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

    const pending = getDashboardSummary();
    const assertion = expect(pending).rejects.toThrow(/timed out/i);

    await vi.advanceTimersByTimeAsync(8000);
    await assertion;
  });
});
