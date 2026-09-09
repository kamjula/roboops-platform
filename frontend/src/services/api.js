const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 8000;
export const ACCESS_TOKEN_KEY = "roboops.access_token";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

async function request(
  path,
  { body, headers = {}, method = "GET", params, skipUnauthorized = false, timeoutMs = DEFAULT_TIMEOUT_MS } = {},
) {
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
    const requestHeaders = { ...headers };
    const token = getAccessToken();
    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }
    response = await fetch(url, { body, headers: requestHeaders, method, signal: controller.signal });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request to ${path} timed out after ${timeoutMs}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const error = new ApiError(
      `Request to ${path} failed: ${response.status} ${response.statusText}`,
      response.status,
    );
    if (response.status === 401 && !skipUnauthorized) {
      window.dispatchEvent(new CustomEvent("roboops:unauthorized"));
    }
    throw error;
  }
  return response.json();
}

export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password });
  return request("/api/v1/auth/login", {
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    method: "POST",
    skipUnauthorized: true,
  });
}

export function getCurrentUser() {
  return request("/api/v1/auth/me", { skipUnauthorized: true });
}

export async function getHealth() {
  return request("/health");
}

export function getRobots({ skip, limit } = {}) {
  return request("/api/v1/robots", { params: { skip, limit } });
}

export function updateRobotStatus(robotId, status) {
  return request(`/api/v1/robots/${robotId}/status`, {
    body: JSON.stringify({ status }),
    headers: { "Content-Type": "application/json" },
    method: "PATCH",
  });
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
