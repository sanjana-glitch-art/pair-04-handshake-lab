function StudentDashboard() {
  return (
    <div className="container py-5">
      <div className="mb-5">
        <h1>Welcome to Handshake</h1>
        <p className="lead text-muted">
          Find jobs, discover events, and build your career.
        </p>
      </div>

      <div className="row g-4">
        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5 className="card-title">Find Jobs</h5>
              <p className="card-text">
                Search for internships, full-time jobs, and on-campus roles.
              </p>
              <a href="/student/jobs" className="btn btn-primary">
                Search Jobs
              </a>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5 className="card-title">Explore Events</h5>
              <p className="card-text">
                Discover career fairs, workshops, and networking events.
              </p>
              <a href="/student/events" className="btn btn-primary">
                View Events
              </a>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h5 className="card-title">AI Assistant</h5>
              <p className="card-text">
                Get help finding jobs and events that match your interests.
              </p>
              <a href="/student/assistant" className="btn btn-primary">
                Open Assistant
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StudentDashboard;