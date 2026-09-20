import { NavLink } from "react-router-dom";

function Navbar() {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
      <div className="container">
        <NavLink className="navbar-brand fw-bold" to="/student/dashboard">
          Handshake
        </NavLink>

        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#studentNavbar"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="studentNavbar">
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

            <NavLink className="nav-link" to="/student/applications">
              Applications
            </NavLink>

            <NavLink className="nav-link" to="/student/events">
              Events
            </NavLink>

            <NavLink className="nav-link" to="/student/assistant">
              Assistant
            </NavLink>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;