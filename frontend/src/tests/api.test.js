import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getDashboardSummary,
  getRobotStatus,
  getSiteSummary,
  getMaintenanceSummary,
  getLatestAlerts,
  getHealthSummary,
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
    await vi.advanceTimersByTimeAsync(8000);

    await expect(pending).rejects.toThrow(/timed out/i);
  });
});
