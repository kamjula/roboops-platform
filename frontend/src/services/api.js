const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 8000;

async function request(path, { params, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const url = new URL(path, BASE_URL);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, { signal: controller.signal });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request to ${path} timed out after ${timeoutMs}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function getHealth() {
  return request("/health");
}

export async function getDashboardSummary() {
  return request("/api/v1/dashboard/summary");
}

export async function getRobotStatus() {
  return request("/api/v1/dashboard/robot-status");
}

export async function getSiteSummary() {
  return request("/api/v1/dashboard/site-summary");
}

export async function getMaintenanceSummary() {
  return request("/api/v1/dashboard/maintenance-summary");
}

export async function getLatestAlerts({ limit } = {}) {
  return request("/api/v1/dashboard/latest-alerts", { params: { limit } });
}

export async function getHealthSummary() {
  return request("/api/v1/dashboard/health-summary");
}
