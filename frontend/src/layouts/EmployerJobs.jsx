import { useEffect, useState } from "react";
import {
  createEmployerJob,
  deleteEmployerJob,
  getEmployerJobs,
  updateEmployerJob,
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
  const [success, setSuccess] = useState("");

  async function loadJobs() {
    try {
      setLoading(true);
      setError("");

      const data = await getEmployerJobs();
      setJobs(data);
    } catch (err) {
      setError(err.message || "Unable to load jobs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function prepareJobData() {
    return {
      title: formData.title,
      deadline: formData.deadline,
      location: formData.location,
      is_remote: formData.is_remote,
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
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setSaving(true);

    try {
      const jobData = prepareJobData();

      if (editingJobId) {
        await updateEmployerJob(
          editingJobId,
          jobData
        );

        setSuccess("Job updated successfully.");
      } else {
        await createEmployerJob(jobData);

        setSuccess("Job created successfully.");
      }

      setFormData(emptyForm);
      setEditingJobId(null);
      await loadJobs();
    } catch (err) {
      setError(err.message || "Unable to save job.");
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(job) {
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

    setSuccess("");
    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  function cancelEdit() {
    setEditingJobId(null);
    setFormData(emptyForm);
    setError("");
    setSuccess("");
  }

  async function handleDelete(jobId) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this job?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setSuccess("");

      await deleteEmployerJob(jobId);

      setSuccess("Job deleted successfully.");
      await loadJobs();
    } catch (err) {
      setError(err.message || "Unable to delete job.");
    }
  }

  return (
    <div className="container py-5">
      <div className="mb-4">
        <p className="text-uppercase text-muted small mb-2">
          Employer portal
        </p>

        <h1>Manage Jobs</h1>

        <p className="text-muted">
          Create and manage job opportunities for students.
        </p>
      </div>

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

      <div className="card shadow-sm mb-5">
        <div className="card-body">
          <h4 className="mb-4">
            {editingJobId
              ? "Edit Job"
              : "Create New Job"}
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
                    Full time
                  </option>

                  <option value="part_time">
                    Part time
                  </option>

                  <option value="on_campus">
                    On campus
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
                  placeholder="San Jose, California"
                  value={formData.location}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">
                  Minimum salary
                </label>

                <input
                  type="number"
                  name="salary_min"
                  className="form-control"
                  min="0"
                  step="0.01"
                  value={formData.salary_min}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">
                  Maximum salary
                </label>

                <input
                  type="number"
                  name="salary_max"
                  className="form-control"
                  min="0"
                  step="0.01"
                  value={formData.salary_max}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-4 d-flex align-items-end">
                <div className="form-check mb-2">
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
                    Remote position
                  </label>
                </div>
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
                    className="btn btn-outline-secondary"
                    onClick={cancelEdit}
                  >
                    Cancel
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
          You have not created any jobs yet.
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
                  <h5>{job.title}</h5>

                  <p className="text-muted mb-2">
                    {job.category} · {job.location}
                  </p>

                  <p className="small">
                    Deadline: {job.deadline}
                  </p>

                  <p>
                    {job.description}
                  </p>

                  <div className="d-flex gap-2">
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={() => handleEdit(job)}
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      className="btn btn-outline-danger"
                      onClick={() => handleDelete(job.id)}
                    >
                      Delete
                    </button>
                  </div>
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