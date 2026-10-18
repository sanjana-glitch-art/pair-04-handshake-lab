import { Link, Outlet } from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

function StudentLayout() {
  return (
    <div className="student-shell">
      <Navbar />

      <div className="student-main">
        <header className="student-topbar">
          <h2>Home</h2>

          <div className="topbar-actions">
            <Link
              to="/student/profile"
              className="profile-avatar-link"
              title="Open student profile"
            >
              <div className="profile-avatar">
                S
              </div>
            </Link>
          </div>
        </header>

        <main className="student-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default StudentLayout;