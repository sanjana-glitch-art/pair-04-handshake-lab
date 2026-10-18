import { Link } from "react-router-dom";

function EmployerDashboard() {
  return (
    <div className="employer-dashboard container py-5">
      <div className="mb-5">
        <p className="text-uppercase text-muted small mb-2">
          Employer portal
        </p>

        <h1>Welcome to your company dashboard</h1>

        <p className="lead text-muted">
          Manage job postings, events, and student applications.
        </p>
      </div>

      <div className="row g-4">
        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5>Manage Jobs</h5>

              <p className="text-muted">
                Create and update job opportunities for students.
              </p>

              <Link
                to="/employer/jobs"
                className="btn btn-primary"
              >
                View Jobs
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5>Manage Events</h5>

              <p className="text-muted">
                Publish career fairs, workshops, and networking events.
              </p>

              <Link
                to="/employer/events"
                className="btn btn-primary"
              >
                View Events
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5>Applications</h5>

              <p className="text-muted">
                Review applications submitted by students.
              </p>

              <Link
                to="/employer/applications"
                className="btn btn-primary"
              >
                View Applications
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EmployerDashboard;