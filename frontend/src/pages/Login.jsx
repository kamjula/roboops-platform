import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function Login() {
  const { login, loginDemo } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(email, password);
      const destination = location.state?.from?.pathname || "/";
      navigate(destination, { replace: true });
    } catch {
      setError("Unable to sign in with those credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDemo() {
    setSubmitting(true);
    setError("");
    try {
      await loginDemo();
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch {
      setError("The read-only demo is unavailable. Please try again shortly.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="eyebrow">RoboOps Platform</div>
        <h1 id="login-title">Sign in</h1>
        <p>Access your robotics operations workspace.</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <div className="demo-entry">
          <p>Explore the synthetic fleet without an account. Demo access is read-only.</p>
          <button type="button" onClick={handleDemo} disabled={submitting}>
            {submitting ? "Opening demo (cold start may take a minute)..." : "Explore read-only demo"}
          </button>
        </div>
      </section>
    </main>
  );
}
