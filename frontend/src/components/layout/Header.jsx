import { Search, Settings, Bell } from "lucide-react";

export default function Header({ title = "Dashboard" } = {}) {
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
          <div className="header-avatar" aria-hidden="true">D</div>
          <span>Demo Workspace</span>
        </div>
      </div>
    </header>
  );
}
