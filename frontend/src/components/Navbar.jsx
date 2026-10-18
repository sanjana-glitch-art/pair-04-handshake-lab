import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function Navbar() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function getNavClass({ isActive }) {
    return isActive
      ? "sidebar-link active"
      : "sidebar-link";
  }

  return (
    <aside className="student-sidebar">
      <NavLink
        to="/student/dashboard"
        className="sidebar-logo"
      >
        H
      </NavLink>

      <nav className="sidebar-navigation">
        <NavLink
          to="/student/dashboard"
          className={getNavClass}
        >
          <span className="sidebar-icon">⌂</span>
          Home
        </NavLink>

        <NavLink
          to="/student/jobs"
          className={getNavClass}
        >
          <span className="sidebar-icon">▣</span>
          Jobs
        </NavLink>

        <NavLink
          to="/student/profile"
          className={getNavClass}
        >
          <span className="sidebar-icon">♙</span>
          Profile
        </NavLink>

        <NavLink
          to="/student/applications"
          className={getNavClass}
        >
          <span className="sidebar-icon">▤</span>
          Applications
        </NavLink>

        <NavLink
          to="/student/events"
          className={getNavClass}
        >
          <span className="sidebar-icon">□</span>
          Events
        </NavLink>

        <NavLink
          to="/student/registered-events"
          className={getNavClass}
        >
          <span className="sidebar-icon">✓</span>
          Registered Events
        </NavLink>

        <NavLink
          to="/student/preferences"
          className={getNavClass}
        >
          <span className="sidebar-icon">⚙</span>
          Preferences
        </NavLink>

        <NavLink
          to="/student/assistant"
          className={getNavClass}
        >
          <span className="sidebar-icon">✦</span>
          AI Assistant
        </NavLink>
      </nav>

      <div className="sidebar-bottom">
        <button
          className="sidebar-logout"
          type="button"
          onClick={handleLogout}
        >
          Log out
        </button>
      </div>
    </aside>
  );
}

export default Navbar;