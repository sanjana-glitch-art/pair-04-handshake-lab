import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  fetchMyApplications,
  selectApplicationFilter,
  selectApplications,
  selectApplicationsError,
  selectApplicationsLoading,
  statusFilterChanged,
} from "../store/slices/applicationsSlice.js";

function Applications() {
  const dispatch = useDispatch();
  const applications = useSelector(selectApplications);
  const loading = useSelector(selectApplicationsLoading);
  const error = useSelector(selectApplicationsError);
  const statusFilter = useSelector(selectApplicationFilter);
  const setStatusFilter = (status) => dispatch(statusFilterChanged(status));

  useEffect(() => {
    dispatch(fetchMyApplications(statusFilter));
  }, [statusFilter, dispatch]);

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

      <div className="btn-group mb-4" role="group" aria-label="Filter by status">
        {["", "Pending", "Reviewed", "Declined"].map((status) => (
          <button
            key={status || "all"}
            type="button"
            className={`btn btn-sm ${
              statusFilter === status ? "btn-dark" : "btn-outline-dark"
            }`}
            onClick={() => setStatusFilter(status)}
          >
            {status || "All"}
          </button>
        ))}
      </div>

      {loading && <p>Loading your applications...</p>}

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {!loading && !error && applications.length === 0 && (
        <div className="alert alert-info">
          {statusFilter
            ? `No ${statusFilter.toLowerCase()} applications.`
            : "You have not submitted any applications yet."}
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