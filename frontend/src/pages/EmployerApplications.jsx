import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchResumeBlobUrl,
  getEmployerApplicationsFiltered,
  getEmployerJobs,
  updateEmployerApplicationStatus,
} from "../services/api.js";

function EmployerApplications() {
  const [searchParams, setSearchParams] = useSearchParams();
  const jobFilter = searchParams.get("job") || "";
  const statusFilter = searchParams.get("status") || "";

  const [applications, setApplications] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Resume preview: object URL of the PDF currently shown.
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    getEmployerJobs()
      .then((data) => setJobs(Array.isArray(data) ? data : []))
      .catch(() => setJobs([]));
  }, []);

  useEffect(() => {
    loadApplications();
  }, [jobFilter, statusFilter]);

  // Free the PDF object URL when it is replaced or the page closes.
  useEffect(() => {
    return () => {
      if (preview?.url) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [preview]);

  async function loadApplications() {
    setLoading(true);
    setError("");

    try {
      const data = await getEmployerApplicationsFiltered({
        jobId: jobFilter,
        status: statusFilter,
      });
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(
        err.message || "Unable to load applications."
      );
    } finally {
      setLoading(false);
    }
  }

  function setFilter(name, value) {
    const next = new URLSearchParams(searchParams);

    if (value) {
      next.set(name, value);
    } else {
      next.delete(name);
    }

    setSearchParams(next);
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

  async function openResume(application) {
    setPreviewLoading(true);
    setError("");

    try {
      const url = await fetchResumeBlobUrl(application.application_id);
      setPreview({ url, name: application.student_name, job: application.job_title });
    } catch (err) {
      setError(err.message);
    } finally {
      setPreviewLoading(false);
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

      <div className="row g-2 mb-4">
        <div className="col-md-6">
          <label className="form-label small" htmlFor="filter-job">Job posting</label>
          <select
            id="filter-job"
            className="form-select"
            value={jobFilter}
            onChange={(event) => setFilter("job", event.target.value)}
          >
            <option value="">All my postings</option>
            {jobs.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title} (#{job.id})
              </option>
            ))}
          </select>
        </div>

        <div className="col-md-3">
          <label className="form-label small" htmlFor="filter-status">Status</label>
          <select
            id="filter-status"
            className="form-select"
            value={statusFilter}
            onChange={(event) => setFilter("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="Pending">Pending</option>
            <option value="Reviewed">Reviewed</option>
            <option value="Declined">Declined</option>
          </select>
        </div>
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

      {preview && (
        <div className="card shadow-sm mb-4">
          <div className="card-header d-flex justify-content-between align-items-center">
            <span>
              Resume: <strong>{preview.name}</strong> for {preview.job}
            </span>
            <button
              type="button"
              className="btn-close"
              aria-label="Close resume preview"
              onClick={() => setPreview(null)}
            />
          </div>
          <iframe
            title="Resume preview"
            src={preview.url}
            style={{ width: "100%", height: "70vh", border: 0 }}
          />
        </div>
      )}

      {loading ? (
        <p>Loading applications...</p>
      ) : applications.length === 0 ? (
        <div className="alert alert-info">
          No applications match these filters.
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
                    <Link to={`/employer/students/${application.student_id}`}>
                      {application.student_name}
                    </Link>
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

                  <button
                    type="button"
                    className="btn btn-outline-primary btn-sm mb-3"
                    onClick={() => openResume(application)}
                    disabled={previewLoading}
                  >
                    {previewLoading ? "Loading..." : "Preview resume (PDF)"}
                  </button>

                  <label className="form-label d-block" htmlFor={`status-${application.application_id}`}>
                    Application status
                  </label>

                  <select
                    id={`status-${application.application_id}`}
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
