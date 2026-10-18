import { useEffect, useState } from "react";
import {
  getJobDetails,
  searchJobs,
  submitApplication,
} from "../services/api.js";

const initialFilters = {
  search: "",
  category: "",
  city: "",
  remote: "",
  min_salary: "",
};

function formatCategory(category) {
  if (!category) return "Opportunity";

  return category
    .replace("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatSalary(min, max) {
  if (!min && !max) return "Salary not listed";

  if (min && max) {
    return `$${Number(min).toLocaleString()} - $${Number(
      max
    ).toLocaleString()}`;
  }

  return `$${Number(min || max).toLocaleString()}`;
}

function getInitials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);

  const [filters, setFilters] = useState(initialFilters);

  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [resume, setResume] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadJobs(currentFilters = filters) {
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const results = await searchJobs(currentFilters);
      setJobs(results);

      if (results.length === 0) {
        setSelectedJobId(null);
        setSelectedJob(null);
        return;
      }

      const selectedStillExists = results.some(
        (job) => job.id === selectedJobId
      );

      const nextJobId = selectedStillExists
        ? selectedJobId
        : results[0].id;

      setSelectedJobId(nextJobId);
      await loadJobDetails(nextJobId);
    } catch (requestError) {
      setError(requestError.message || "Unable to load jobs.");
      setJobs([]);
      setSelectedJob(null);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobDetails(jobId) {
    if (!jobId) return;

    setDetailsLoading(true);
    setError("");
    setSuccess("");

    try {
      const details = await getJobDetails(jobId);
      setSelectedJob(details);
    } catch (requestError) {
      setError(
        requestError.message || "Unable to load job details."
      );
      setSelectedJob(null);
    } finally {
      setDetailsLoading(false);
    }
  }

  useEffect(() => {
    loadJobs(initialFilters);
  }, []);

  function handleFilterChange(event) {
    const { name, value } = event.target;

    setFilters((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSearch(event) {
    event.preventDefault();
    await loadJobs(filters);
  }

  async function handleReset() {
    setFilters(initialFilters);
    await loadJobs(initialFilters);
  }

  async function handleSelectJob(jobId) {
    setSelectedJobId(jobId);
    await loadJobDetails(jobId);
  }

  function handleResumeChange(event) {
    setResume(event.target.files[0] || null);
    setError("");
    setSuccess("");
  }

  async function handleApply(event) {
    event.preventDefault();

    if (!selectedJob) {
      setError("Please select a job first.");
      return;
    }

    if (!resume) {
      setError("Please select a resume PDF.");
      return;
    }

    if (resume.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }

    const confirmed = window.confirm(
      `Submit your application for "${selectedJob.title}"?`
    );

    if (!confirmed) {
      return;
    }

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      await submitApplication(selectedJob.id, resume);

      setSuccess(
        "Your application was submitted successfully."
      );

      setResume(null);

      const fileInput = document.getElementById(
        "resume-upload"
      );

      if (fileInput) {
        fileInput.value = "";
      }
    } catch (requestError) {
      setError(
        requestError.message ||
          "Unable to submit your application."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="jobs-page-shell">
      <header className="jobs-global-header">
        <div className="jobs-heading">
          <p className="dashboard-eyebrow">OPPORTUNITIES</p>

          <h1>Find your next opportunity</h1>
        </div>

        <form
          className="jobs-global-search"
          onSubmit={handleSearch}
        >
          <input
            type="search"
            name="search"
            placeholder="Search jobs or companies"
            value={filters.search}
            onChange={handleFilterChange}
          />

          <select
            name="category"
            value={filters.category}
            onChange={handleFilterChange}
          >
            <option value="">All categories</option>
            <option value="internship">Internship</option>
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="on_campus">On-campus</option>
          </select>

          <input
            type="text"
            name="city"
            placeholder="City"
            value={filters.city}
            onChange={handleFilterChange}
          />

          <select
            name="remote"
            value={filters.remote}
            onChange={handleFilterChange}
          >
            <option value="">Any work mode</option>
            <option value="true">Remote</option>
            <option value="false">On-site</option>
          </select>

          <input
            type="number"
            name="min_salary"
            placeholder="Minimum salary"
            min="0"
            value={filters.min_salary}
            onChange={handleFilterChange}
          />

          <button
            type="submit"
            className="jobs-search-button"
          >
            Search
          </button>

          <button
            type="button"
            className="jobs-reset-button"
            onClick={handleReset}
          >
            Reset
          </button>
        </form>
      </header>

      {error && (
        <div className="jobs-message jobs-error">
          {error}
        </div>
      )}

      {success && (
        <div className="jobs-message jobs-success">
          {success}
        </div>
      )}

      <div className="jobs-split-page">
        <aside className="jobs-browser-panel">
          <div className="jobs-browser-header">
            <div>
              <p className="dashboard-eyebrow">
                MATCHED ROLES
              </p>

              <h2>Job opportunities</h2>
            </div>

            <span>{jobs.length} results</span>
          </div>

          {loading ? (
            <p className="jobs-empty-text">
              Loading jobs...
            </p>
          ) : jobs.length === 0 ? (
            <p className="jobs-empty-text">
              No jobs match your search.
            </p>
          ) : (
            <div className="jobs-list">
              {jobs.map((job) => (
                <button
                  type="button"
                  key={job.id}
                  className={
                    selectedJobId === job.id
                      ? "job-list-card selected"
                      : "job-list-card"
                  }
                  onClick={() => handleSelectJob(job.id)}
                >
                  <div className="company-square">
                    {getInitials(job.company_name)}
                  </div>

                  <div className="job-list-card-content">
                    <h3>{job.title}</h3>

                    <p>{job.company_name}</p>

                    <small>
                      {job.location}
                      {job.is_remote ? " · Remote" : ""}
                    </small>
                  </div>
                </button>
              ))}
            </div>
          )}
        </aside>

        <main className="job-detail-panel">
          {detailsLoading ? (
            <div className="job-detail-empty">
              <p>Loading job details...</p>
            </div>
          ) : !selectedJob ? (
            <div className="job-detail-empty">
              <h2>Select a job</h2>
              <p>
                Choose an opportunity from the list to view
                its details.
              </p>
            </div>
          ) : (
            <article className="job-detail-content">
              <div className="job-detail-top">
                <div className="company-large-square">
                  {getInitials(selectedJob.company_name)}
                </div>

                <div>
                  <p className="dashboard-eyebrow">
                    {formatCategory(selectedJob.category)}
                  </p>

                  <h1>{selectedJob.title}</h1>

                  <p className="job-company-name">
                    {selectedJob.company_name}
                  </p>
                </div>
              </div>

              <div className="job-detail-meta">
                <span>📍 {selectedJob.location}</span>

                <span>
                  {selectedJob.is_remote
                    ? "Remote"
                    : "On-site"}
                </span>

                <span>
                  💰{" "}
                  {formatSalary(
                    selectedJob.salary_min,
                    selectedJob.salary_max
                  )}
                </span>

                <span>
                  Deadline: {selectedJob.deadline}
                </span>
              </div>

              <hr />

              <section className="job-description-section">
                <h2>About this opportunity</h2>

                <p>
                  {selectedJob.description ||
                    "No description provided."}
                </p>
              </section>

              <section className="job-application-section">
                <h2>Apply for this job</h2>

                <p>
                  Upload your resume as a PDF to submit your
                  application.
                </p>

                <form onSubmit={handleApply}>
                  <label htmlFor="resume-upload">
                    Resume PDF
                  </label>

                  <input
                    id="resume-upload"
                    type="file"
                    accept="application/pdf,.pdf"
                    onChange={handleResumeChange}
                  />

                  <button
                    type="submit"
                    className="job-apply-button"
                    disabled={submitting}
                  >
                    {submitting
                      ? "Submitting..."
                      : "Submit application"}
                  </button>
                </form>
              </section>
            </article>
          )}
        </main>
      </div>
    </div>
  );
}

export default Jobs;