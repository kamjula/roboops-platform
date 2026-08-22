import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import Sidebar from "../components/layout/Sidebar.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import Login from "../pages/Login.jsx";

const Dashboard = lazy(() => import("../pages/Dashboard.jsx"));
const Robots = lazy(() => import("../pages/Robots.jsx"));
const Telemetry = lazy(() => import("../pages/Telemetry.jsx"));
const Health = lazy(() => import("../pages/Health.jsx"));
const Tasks = lazy(() => import("../pages/Tasks.jsx"));
const Alerts = lazy(() => import("../pages/Alerts.jsx"));
const Maintenance = lazy(() => import("../pages/Maintenance.jsx"));
const Analytics = lazy(() => import("../pages/Analytics.jsx"));
const AIAssistant = lazy(() => import("../pages/AIAssistant.jsx"));
const Settings = lazy(() => import("../pages/Settings.jsx"));

function ProtectedLayout() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") {
    return <LoadingState label="Restoring your session..." />;
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/robots" element={<Robots />} />
          <Route path="/telemetry" element={<Telemetry />} />
          <Route path="/health" element={<Health />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/maintenance" element={<Maintenance />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/ai-assistant" element={<AIAssistant />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function AppRoutes() {
  const { status } = useAuth();
  return (
    <Suspense fallback={<LoadingState label="Loading page..." />}>
      <Routes>
        <Route path="/login" element={status === "authenticated" ? <Navigate to="/" replace /> : <Login />} />
        <Route path="*" element={<ProtectedLayout />} />
      </Routes>
    </Suspense>
  );
}
