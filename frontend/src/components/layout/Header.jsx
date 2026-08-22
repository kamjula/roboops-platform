import { Search, Settings, Bell } from "lucide-react";
import { useAuth } from "../../auth/AuthContext.jsx";

export default function Header({ title = "Dashboard" } = {}) {
  const { logout, user } = useAuth();
  return (
    <header className="app-header">
      <h1 className="header-title">{title}</h1>
      <div className="header-actions">
        <span className="icon-button" aria-hidden="true">
          <Search size={18} />
        </span>
        <span className="icon-button" aria-hidden="true">
          <Bell size={18} />
        </span>
        <span className="icon-button" aria-hidden="true">
          <Settings size={18} />
        </span>
        <div className="header-user">
          {user ? <div className="header-avatar" aria-hidden="true">{user.email[0].toUpperCase()}</div> : null}
          <span>{user ? `${user.email} (${user.role})` : "Restoring session..."}</span>
        </div>
        {user ? <button type="button" className="logout-button" onClick={logout}>Log out</button> : null}
      </div>
    </header>
  );
}
