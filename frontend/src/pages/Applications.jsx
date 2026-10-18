import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMyApplications } from "../services/api.js";

function Applications() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadApplications() {
      try {
        setLoading(true);
        setError("");

        const data = await getMyApplications();

        setApplications(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(
          err.message || "Unable to load your applications."
        );
      } finally {
        setLoading(false);
      }
    }

    loadApplications();
  }, []);

  function formatDate(dateValue) {
    if (!dateValue) {
      return "Not available";
    }

    return new Date(dateValue).toLocaleDateString();
  }

  function getStatusClass(status) {
    if (status === "Pending") {
      return "bg-warning text-dark";
    }

    if (status === "Reviewed") {
      return "bg-success";
    }

    if (status === "Declined") {
      return "bg-danger";
    }

    return "bg-secondary";
  }

  return (
    <div className="container py-5">
      <div className="mb-4">
        <h1>My Applications</h1>

        <p className="text-muted">
          View the jobs you have applied for and track their status.
        </p>
      </div>

      {loading && <p>Loading your applications...</p>}

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {!loading && !error && applications.length === 0 && (
        <div className="alert alert-info">
          You have not submitted any applications yet.
        </div>
      )}

      {!loading && !error && applications.length > 0 && (
        <div className="row g-4">
          {applications.map((application) => (
            <div
              className="col-md-6"
              key={application.id}
            >
              <div className="card h-100 shadow-sm border-0">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start mb-3">
                    <span
                      className={`badge ${getStatusClass(
                        application.status
                      )}`}
                    >
                      {application.status}
                    </span>

                    <small className="text-muted">
                      Application #{application.id}
                    </small>
                  </div>

                  <h4 className="card-title">
                    {application.job_title}
                  </h4>

                  <h6 className="text-muted mb-3">
                    {application.company_name}
                  </h6>

                  <p className="mb-2">
                    <strong>Applied on:</strong>{" "}
                    {formatDate(application.applied_at)}
                  </p>

                  <p className="mb-3">
                    <strong>Resume:</strong> Uploaded
                  </p>

                  <Link
                    to={`/student/jobs/${application.job_id}`}
                    className="btn btn-outline-primary"
                  >
                    View Job
                  </Link> 
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Applications;