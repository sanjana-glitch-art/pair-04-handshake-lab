import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getJobDetails,
  submitApplication,
} from "../services/api.js";

function JobDetails() {
  const { jobId } = useParams();

  const [job, setJob] = useState(null);
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadJob() {
      try {
        setLoading(true);
        setError("");

        const data = await getJobDetails(jobId);
        setJob(data);
      } catch (err) {
        setError(err.message || "Unable to load job details.");
      } finally {
        setLoading(false);
      }
    }

    loadJob();
  }, [jobId]);

  function handleResumeChange(event) {
    const selectedFile = event.target.files[0];

    setError("");
    setSuccess("");

    if (!selectedFile) {
      setResume(null);
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      setResume(null);
      return;
    }

    if (selectedFile.size > 5 * 1024 * 1024) {
      setError("The PDF must be smaller than 5 MB.");
      setResume(null);
      return;
    }

    setResume(selectedFile);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!resume) {
      setError("Please choose a PDF resume first.");
      return;
    }

    try {
      setSubmitting(true);
      setError("");
      setSuccess("");

      const result = await submitApplication(jobId, resume);

      setSuccess(
        result.message || "Application submitted successfully."
      );

      setResume(null);
      event.target.reset();
    } catch (err) {
      setError(err.message || "Unable to submit application.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="container py-5">
        <p>Loading job details...</p>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="container py-5">
        <div className="alert alert-danger">{error}</div>

        <Link
          to="/student/jobs"
          className="btn btn-primary"
        >
          Back to Jobs
        </Link>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="container py-5">
        <p>Job not found.</p>
      </div>
    );
  }

  return (
    <div className="container py-5">
      <Link
        to="/student/jobs"
        className="btn btn-link px-0 mb-3"
      >
        ← Back to Jobs
      </Link>

      <div className="card shadow-sm border-0">
        <div className="card-body p-4">
          <span className="badge bg-primary mb-3">
            {job.category}
          </span>

          <h1>{job.title}</h1>

          <h4 className="text-muted">
            {job.company_name}
          </h4>

          <hr />

          <p>
            <strong>Location:</strong> {job.location}
          </p>

          <p>
            <strong>Work mode:</strong>{" "}
            {job.is_remote ? "Remote" : "On-site"}
          </p>

          <p>
            <strong>Salary:</strong>{" "}
            {job.salary_min || job.salary_max
              ? `$${job.salary_min || ""} - $${job.salary_max || ""}`
              : "Not listed"}
          </p>

          <p>
            <strong>Posted:</strong> {job.posted_date}
          </p>

          <p>
            <strong>Application deadline:</strong>{" "}
            {job.deadline}
          </p>

          <h4 className="mt-4">Job Description</h4>

          <p>{job.description}</p>

          <h4 className="mt-4">Company Information</h4>

          <p>
            {job.company_description ||
              "No company description available."}
          </p>

          <p>
            <strong>Company location:</strong>{" "}
            {job.company_location || "Not listed"}
          </p>

          <p>
            <strong>Contact email:</strong>{" "}
            {job.contact_email || "Not listed"}
          </p>

          <hr className="my-4" />

          <h4>Apply for this job</h4>

          <p className="text-muted">
            Upload your resume as a PDF file. Maximum size: 5 MB.
          </p>

          {error && (
            <div className="alert alert-danger">
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label
                htmlFor="resume"
                className="form-label"
              >
                PDF Resume
              </label>

              <input
                id="resume"
                name="resume"
                type="file"
                className="form-control"
                accept=".pdf,application/pdf"
                onChange={handleResumeChange}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting
                ? "Submitting..."
                : "Submit Application"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default JobDetails;