import { useEffect, useState } from "react";
import {
  getEmployerApplications,
  updateEmployerApplicationStatus,
} from "../services/api.js";

function EmployerApplications() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadApplications();
  }, []);

  async function loadApplications() {
    setLoading(true);
    setError("");

    try {
      const data = await getEmployerApplications();
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(
        err.message || "Unable to load applications."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(applicationId, status) {
    setError("");
    setMessage("");

    try {
      const updatedApplication =
        await updateEmployerApplicationStatus(
          applicationId,
          status
        );

      setApplications((previous) =>
        previous.map((application) =>
          application.application_id === applicationId
            ? updatedApplication
            : application
        )
      );

      setMessage("Application status updated successfully.");
    } catch (err) {
      setError(
        err.message || "Unable to update application status."
      );
    }
  }

  return (
    <div className="container py-5">
      <div className="mb-4">
        <h1>Student Applications</h1>

        <p className="text-muted">
          Review applications submitted to your jobs.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {message && (
        <div className="alert alert-success">
          {message}
        </div>
      )}

      {loading ? (
        <p>Loading applications...</p>
      ) : applications.length === 0 ? (
        <div className="alert alert-info">
          No applications have been submitted to your jobs yet.
        </div>
      ) : (
        <div className="row g-4">
          {applications.map((application) => (
            <div
              className="col-md-6"
              key={application.application_id}
            >
              <div className="card h-100 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title">
                    {application.student_name}
                  </h5>

                  <p className="mb-2">
                    <strong>Email:</strong>{" "}
                    {application.student_email}
                  </p>

                  <p className="mb-2">
                    <strong>Applied for:</strong>{" "}
                    {application.job_title}
                  </p>

                  <p className="mb-2">
                    <strong>Applied on:</strong>{" "}
                    {new Date(
                      application.applied_at
                    ).toLocaleString()}
                  </p>

                  <p className="mb-3">
                    <strong>Resume:</strong>{" "}
                    {application.resume_path}
                  </p>

                  <label className="form-label">
                    Application status
                  </label>

                  <select
                    className="form-select"
                    value={application.status}
                    onChange={(event) =>
                      handleStatusChange(
                        application.application_id,
                        event.target.value
                      )
                    }
                  >
                    <option value="Pending">
                      Pending
                    </option>

                    <option value="Reviewed">
                      Reviewed
                    </option>

                    <option value="Declined">
                      Declined
                    </option>
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default EmployerApplications;