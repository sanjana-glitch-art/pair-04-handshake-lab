import { Link } from "react-router-dom";

function EmployerDashboard() {
  return (
    <div className="employer-dashboard">
      <section className="employer-hero">
        <div>
          <p className="employer-eyebrow">
            EMPLOYER PORTAL
          </p>

          <h1>Build your next great team.</h1>

          <p>
            Connect with talented students, post opportunities,
            and manage your recruiting activity in one place.
          </p>
        </div>

        <Link
          to="/employer/jobs"
          className="employer-primary-button"
        >
          Post a job
        </Link>
      </section>

      <section className="employer-section-heading">
        <div>
          <p className="employer-eyebrow">
            QUICK ACTIONS
          </p>

          <h2>Manage your recruiting</h2>
        </div>
      </section>

      <section className="employer-action-grid">
        <Link
          to="/employer/jobs"
          className="employer-action-card"
        >
          <div className="employer-card-icon">J</div>

          <h3>Job postings</h3>

          <p>
            Create, update, and manage job opportunities for
            students.
          </p>

          <span>Manage jobs →</span>
        </Link>

        <Link
          to="/employer/events"
          className="employer-action-card"
        >
          <div className="employer-card-icon">E</div>

          <h3>Career events</h3>

          <p>
            Publish career fairs, workshops, and networking
            events.
          </p>

          <span>Manage events →</span>
        </Link>

        <Link
          to="/employer/applications"
          className="employer-action-card"
        >
          <div className="employer-card-icon">A</div>

          <h3>Applications</h3>

          <p>
            Review student applications submitted to your jobs.
          </p>

          <span>Review applications →</span>
        </Link>
      </section>

      <section className="employer-info-banner">
        <div>
          <p className="employer-eyebrow">
            PAIR 04 HANDSHAKE
          </p>

          <h2>Find the right students for your team.</h2>

          <p>
            San Jose · Santa Clara · Milpitas
          </p>
        </div>

        <div className="employer-team-badge">
          Team 4
        </div>
      </section>
    </div>
  );
}

export default EmployerDashboard;