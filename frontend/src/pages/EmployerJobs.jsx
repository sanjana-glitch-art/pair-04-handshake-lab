import { useEffect, useState } from "react";
import {
  getEmployerJobs,
  createEmployerJob,
  updateEmployerJob,
  deleteEmployerJob,
} from "../services/api.js";

const emptyForm = {
  title: "",
  deadline: "",
  location: "",
  is_remote: false,
  salary_min: "",
  salary_max: "",
  description: "",
  category: "internship",
};

function EmployerJobs() {
  const [jobs, setJobs] = useState([]);
  const [formData, setFormData] = useState(emptyForm);
  const [editingJobId, setEditingJobId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    setLoading(true);
    setError("");

    try {
      const data = await getEmployerJobs();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Unable to load jobs.");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function resetForm() {
    setFormData(emptyForm);
    setEditingJobId(null);
  }

  function startEditing(job) {
    setEditingJobId(job.id);

    setFormData({
      title: job.title || "",
      deadline: job.deadline || "",
      location: job.location || "",
      is_remote: Boolean(job.is_remote),
      salary_min: job.salary_min ?? "",
      salary_max: job.salary_max ?? "",
      description: job.description || "",
      category: job.category || "internship",
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);

    const payload = {
      title: formData.title,
      deadline: formData.deadline,
      location: formData.location,
      is_remote: Boolean(formData.is_remote),
      salary_min:
        formData.salary_min === ""
          ? null
          : Number(formData.salary_min),
      salary_max:
        formData.salary_max === ""
          ? null
          : Number(formData.salary_max),
      description: formData.description,
      category: formData.category,
    };

    try {
      if (editingJobId) {
        await updateEmployerJob(editingJobId, payload);
        setMessage("Job updated successfully.");
      } else {
        await createEmployerJob(payload);
        setMessage("Job created successfully.");
      }

      resetForm();
      await loadJobs();
    } catch (err) {
      setError(err.message || "Unable to save job.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(jobId) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this job?"
    );

    if (!confirmed) {
      return;
    }

    setError("");
    setMessage("");

    try {
      await deleteEmployerJob(jobId);
      setMessage("Job deleted successfully.");

      if (editingJobId === jobId) {
        resetForm();
      }

      await loadJobs();
    } catch (err) {
      setError(err.message || "Unable to delete job.");
    }
  }

  return (
    <div className="container py-5">
      <div className="mb-4">
        <h1>Manage Jobs</h1>
        <p className="text-muted">
          Create, update, and manage your job postings.
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

      <div className="card shadow-sm mb-5">
        <div className="card-body">
          <h4 className="mb-4">
            {editingJobId ? "Edit Job" : "Create a Job"}
          </h4>

          <form onSubmit={handleSubmit}>
            <div className="row g-3">
              <div className="col-md-8">
                <label className="form-label">
                  Job title
                </label>

                <input
                  type="text"
                  name="title"
                  className="form-control"
                  value={formData.title}
                  onChange={handleChange}
                  placeholder="Example: Data Analyst Intern"
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">
                  Category
                </label>

                <select
                  name="category"
                  className="form-select"
                  value={formData.category}
                  onChange={handleChange}
                  required
                >
                  <option value="internship">
                    Internship
                  </option>

                  <option value="full_time">
                    Full-time
                  </option>

                  <option value="part_time">
                    Part-time
                  </option>

                  <option value="on_campus">
                    On-campus
                  </option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label">
                  Application deadline
                </label>

                <input
                  type="date"
                  name="deadline"
                  className="form-control"
                  value={formData.deadline}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">
                  Location
                </label>

                <input
                  type="text"
                  name="location"
                  className="form-control"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="San Jose, California"
                  required
                />
              </div>

              <div className="col-12">
                <div className="form-check">
                  <input
                    type="checkbox"
                    name="is_remote"
                    className="form-check-input"
                    id="isRemote"
                    checked={formData.is_remote}
                    onChange={handleChange}
                  />

                  <label
                    className="form-check-label"
                    htmlFor="isRemote"
                  >
                    This job is remote
                  </label>
                </div>
              </div>

              <div className="col-md-6">
                <label className="form-label">
                  Minimum salary
                </label>

                <input
                  type="number"
                  name="salary_min"
                  className="form-control"
                  value={formData.salary_min}
                  onChange={handleChange}
                  placeholder="Optional"
                  min="0"
                  step="0.01"
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">
                  Maximum salary
                </label>

                <input
                  type="number"
                  name="salary_max"
                  className="form-control"
                  value={formData.salary_max}
                  onChange={handleChange}
                  placeholder="Optional"
                  min="0"
                  step="0.01"
                />
              </div>

              <div className="col-12">
                <label className="form-label">
                  Job description
                </label>

                <textarea
                  name="description"
                  className="form-control"
                  rows="5"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Describe the job responsibilities and requirements."
                  required
                />
              </div>

              <div className="col-12">
                <button
                  type="submit"
                  className="btn btn-primary me-2"
                  disabled={saving}
                >
                  {saving
                    ? "Saving..."
                    : editingJobId
                      ? "Update Job"
                      : "Create Job"}
                </button>

                {editingJobId && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={resetForm}
                  >
                    Cancel Edit
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>

      <h3 className="mb-3">Your Job Postings</h3>

      {loading ? (
        <p>Loading jobs...</p>
      ) : jobs.length === 0 ? (
        <div className="alert alert-info">
          You have not posted any jobs yet.
        </div>
      ) : (
        <div className="row g-4">
          {jobs.map((job) => (
            <div
              className="col-md-6"
              key={job.id}
            >
              <div className="card h-100 shadow-sm">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <h5 className="card-title">
                      {job.title}
                    </h5>

                    <span className="badge bg-primary">
                      {job.category}
                    </span>
                  </div>

                  <p className="text-muted mb-2">
                    {job.location}
                    {job.is_remote ? " · Remote" : ""}
                  </p>

                  <p className="card-text">
                    {job.description}
                  </p>

                  <p className="mb-2">
                    <strong>Deadline:</strong>{" "}
                    {job.deadline}
                  </p>

                  {(job.salary_min !== null ||
                    job.salary_max !== null) && (
                    <p className="mb-3">
                      <strong>Salary:</strong>{" "}
                      {job.salary_min ?? "—"} -{" "}
                      {job.salary_max ?? "—"}
                    </p>
                  )}

                  <button
                    type="button"
                    className="btn btn-outline-primary btn-sm me-2"
                    onClick={() => startEditing(job)}
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="btn btn-outline-danger btn-sm"
                    onClick={() => handleDelete(job.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default EmployerJobs;