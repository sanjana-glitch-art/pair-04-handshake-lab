import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function Navbar() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
      <div className="container">
        <NavLink
          className="navbar-brand fw-bold"
          to="/student/dashboard"
        >
          Handshake
        </NavLink>

        <div className="navbar-nav ms-auto">
          <NavLink className="nav-link" to="/student/dashboard">
            Dashboard
          </NavLink>

          <NavLink className="nav-link" to="/student/profile">
            Profile
          </NavLink>

          <NavLink className="nav-link" to="/student/jobs">
            Jobs
          </NavLink>

          <NavLink
            className="nav-link"
            to="/student/applications"
          >
            Applications
          </NavLink>

          <NavLink className="nav-link" to="/student/events">
            Events
          </NavLink>

          <NavLink className="nav-link" to="/student/assistant">
            Assistant
          </NavLink>

          <button
            className="btn btn-outline-light btn-sm ms-3"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;