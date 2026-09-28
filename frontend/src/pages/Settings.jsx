import { useAuth } from "../auth/AuthContext.jsx";
import Header from "../components/layout/Header.jsx";

export default function Settings() {
  const { user } = useAuth();
  return <section className="page action-page">
    <Header title="Settings" />
    <div className="eyebrow">Account & workspace</div>
    <h2>Session information</h2>
    <p>Account details for this signed-in session. Configuration is managed by the deployment operator; this page does not modify server settings.</p>
    <section className="analytics-panel" aria-label="Account details">
      <dl className="account-details"><dt>Email</dt><dd>{user?.email || "Unavailable"}</dd><dt>Role</dt><dd>{user?.role || "Unavailable"}</dd><dt>Workspace data</dt><dd>{user?.email === "demo@roboops.example" ? "Synthetic demonstration fleet" : "Configured fleet database"}</dd></dl>
    </section>
  </section>;
}
