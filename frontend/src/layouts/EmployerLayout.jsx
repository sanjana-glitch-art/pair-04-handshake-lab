import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function EmployerLayout() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function linkClass({ isActive }) {
    return isActive
      ? "sidebar-link active"
      : "sidebar-link";
  }

  return (
    <div className="student-shell">
      <aside className="student-sidebar">
        <NavLink
          to="/employer/dashboard"
          className="sidebar-logo"
        >
          H
        </NavLink>

        <nav className="sidebar-navigation">
          <NavLink
            to="/employer/dashboard"
            className={linkClass}
          >
            <span className="sidebar-icon">⌂</span>
            Dashboard
          </NavLink>

          <NavLink
            to="/employer/jobs"
            className={linkClass}
          >
            <span className="sidebar-icon">▣</span>
            Jobs
          </NavLink>

          <NavLink
            to="/employer/events"
            className={linkClass}
          >
            <span className="sidebar-icon">◫</span>
            Events
          </NavLink>

          <NavLink
            to="/employer/applications"
            className={linkClass}
          >
            <span className="sidebar-icon">✓</span>
            Applications
          </NavLink>

          <NavLink
            to="/employer/students"
            className={linkClass}
          >
            <span className="sidebar-icon">☺</span>
            Students
          </NavLink>
        </nav>

        <NavLink
          to="/employer/profile"
          className={linkClass}
        >
          <span className="sidebar-icon">◉</span>
          Company profile
          </NavLink>

        <div className="sidebar-bottom">
          <p className="text-muted small px-3">
            Employer portal
          </p>

          <button
            type="button"
            className="sidebar-logout"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="student-main employer-main">
        <header className="student-topbar">
          <h2>Employer portal</h2>

          <span className="topbar-role">
            Company account
          </span>
        </header>

        <Outlet />
      </main>
    </div>
  );
}

export default EmployerLayout;