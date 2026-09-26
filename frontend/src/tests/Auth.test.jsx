import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import { AuthProvider, useAuth } from "../auth/AuthContext.jsx";
import Header from "../components/layout/Header.jsx";
import { ACCESS_TOKEN_KEY } from "../services/api.js";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  loginDemo: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("../services/api.js", () => ({
  ACCESS_TOKEN_KEY: "roboops.access_token",
  getCurrentUser: api.getCurrentUser,
  login: api.login,
  loginDemo: api.loginDemo,
  logout: api.logout,
}));

function AuthProbe() {
  const { logout, status, user } = useAuth();
  const location = useLocation();
  return (
    <>
      <output data-testid="status">{status}</output>
      {user ? <output data-testid="user">{user.email} ({user.role})</output> : null}
      <output data-testid="location">{location.pathname}</output>
      {user ? <button onClick={logout}>Log out</button> : null}
    </>
  );
}

function renderAuth(initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("authentication flow", () => {
  beforeEach(() => {
    sessionStorage.clear();
    api.getCurrentUser.mockReset();
    api.login.mockReset();
    api.loginDemo.mockReset();
    api.logout.mockReset();
    api.logout.mockResolvedValue(null);
  });

  it("starts unauthenticated without a stored token", async () => {
    renderAuth();
    expect(await screen.findByTestId("status")).toHaveTextContent("unauthenticated");
    expect(api.getCurrentUser).not.toHaveBeenCalled();
  });

  it("bootstraps a stored token from the current-user endpoint", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    api.getCurrentUser.mockResolvedValue({ email: "viewer@example.com", role: "viewer" });
    renderAuth();
    expect(await screen.findByTestId("user")).toHaveTextContent("viewer@example.com (viewer)");
    expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
  });

  it("clears an invalid stored token", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "expired-token");
    api.getCurrentUser.mockRejectedValue({ status: 401 });
    renderAuth();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
  });

  it("stores the login token and database-backed user", async () => {
    api.login.mockResolvedValue({ access_token: "new-token" });
    api.getCurrentUser.mockResolvedValue({ email: "operator@example.com", role: "operator" });
    function LoginProbe() {
      const { login } = useAuth();
      return <button onClick={() => login("operator@example.com", "secret")}>Authenticate</button>;
    }
    render(<MemoryRouter><AuthProvider><LoginProbe /><AuthProbe /></AuthProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Authenticate" }));
    expect(await screen.findByTestId("user")).toHaveTextContent("operator@example.com (operator)");
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBe("new-token");
  });

  it("opens a viewer demo without asking for a password", async () => {
    api.loginDemo.mockResolvedValue({ access_token: "demo-token" });
    api.getCurrentUser.mockResolvedValue({ email: "demo@roboops.example", role: "viewer" });
    function DemoProbe() {
      const { loginDemo } = useAuth();
      return <button onClick={loginDemo}>Explore read-only demo</button>;
    }
    render(<MemoryRouter><AuthProvider><DemoProbe /><AuthProbe /></AuthProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Explore read-only demo" }));
    expect(await screen.findByTestId("user")).toHaveTextContent("demo@roboops.example (viewer)");
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBe("demo-token");
  });

  it("revokes the server session, clears the token, and navigates to login", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    api.getCurrentUser.mockResolvedValue({ email: "admin@example.com", role: "admin" });
    renderAuth();
    await screen.findByRole("button", { name: "Log out" });
    fireEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(api.logout).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(screen.getByTestId("location")).toHaveTextContent("/login");
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
  });

  it("clears the session when an authenticated request emits a 401", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    api.getCurrentUser.mockResolvedValue({ email: "viewer@example.com", role: "viewer" });
    renderAuth();
    await screen.findByTestId("user");
    await act(async () => {
      window.dispatchEvent(new CustomEvent("roboops:unauthorized"));
    });
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
  });

  it("shows the authenticated email and role in Header and logs out", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    api.getCurrentUser.mockResolvedValue({ email: "admin@example.com", role: "admin" });
    render(<MemoryRouter><AuthProvider><Header title="Dashboard" /></AuthProvider></MemoryRouter>);
    expect(await screen.findByText("admin@example.com (admin)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull());
  });

  it("clears the browser session even when server logout fails", async () => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, "stored-token");
    api.getCurrentUser.mockResolvedValue({ email: "admin@example.com", role: "admin" });
    api.logout.mockRejectedValue(new Error("network unavailable"));
    renderAuth();
    await screen.findByRole("button", { name: "Log out" });
    fireEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(sessionStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull());
    expect(screen.getByTestId("location")).toHaveTextContent("/login");
  });
});

it("protects application routes and leaves login outside the Sidebar", async () => {
  api.getCurrentUser.mockResolvedValue(undefined);
  render(<MemoryRouter initialEntries={["/robots"]}><App /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.queryByText("RoboOps")).not.toBeInTheDocument();
});
