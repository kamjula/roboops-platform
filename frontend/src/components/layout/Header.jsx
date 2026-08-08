import { Search, Settings, Bell } from "lucide-react";

export default function Header({ title = "Dashboard" } = {}) {
  return (
    <header className="app-header">
      <h2 className="header-title">{title}</h2>
      <div className="header-actions">
        <button type="button" className="icon-button" aria-label="Search">
          <Search size={18} />
        </button>
        <button type="button" className="icon-button" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <button type="button" className="icon-button" aria-label="Settings">
          <Settings size={18} />
        </button>
        <div className="header-user">
          <div className="header-avatar" aria-hidden="true">A</div>
          <span>Admin Demo</span>
        </div>
      </div>
    </header>
  );
}
