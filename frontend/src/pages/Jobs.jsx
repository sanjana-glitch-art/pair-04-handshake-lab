import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { searchJobs } from "../services/api.js";

function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [filters, setFilters] = useState({
    search: "",
    category: "",
    city: "",
    remote: "",
    min_salary: "",
  });

  async function loadJobs(currentFilters = {}) {
    try {
      setLoading(true);
      setError("");

      const data = await searchJobs(currentFilters);

      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Job loading error:", err);
      setError(err.message || "Unable to load jobs.");
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadJobs({});
  }, []);

  function handleChange(event) {
    const { name, value } = event.target;

    setFilters((previousFilters) => ({
      ...previousFilters,
      [name]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    loadJobs(filters);
  }

  function handleReset() {
    const emptyFilters = {
      search: "",
      category: "",
      city: "",
      remote: "",
      min_salary: "",
    };

    setFilters(emptyFilters);
    loadJobs(emptyFilters);
  }

  function formatSalary(job) {
    if (!job.salary_min && !job.salary_max) {
      return "Salary not listed";
    }

    if (job.salary_min && job.salary_max) {
      return `$${job.salary_min} - $${job.salary_max}`;
    }

    return `$${job.salary_min || job.salary_max}`;
  }

  return (
    <div className="container py-5">
      <h1>Find Jobs</h1>

      <p className="text-muted">
        Search for internships and job opportunities.
      </p>

      <form onSubmit={handleSubmit} className="card shadow-sm border-0 mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <label htmlFor="search" className="form-label">
                Search
              </label>

              <input
                id="search"
                name="search"
                type="text"
                className="form-control"
                placeholder="Search by job title"
                value={filters.search}
                onChange={handleChange}
              />
            </div>

            <div className="col-md-3">
              <label htmlFor="category" className="form-label">
                Category
              </label>

              <select
                id="category"
                name="category"
                className="form-select"
                value={filters.category}
                onChange={handleChange}
              >
                <option value="">All categories</option>
                <option value="internship">Internship</option>
                <option value="full_time">Full-time</option>
                <option value="part_time">Part-time</option>
                <option value="on_campus">On-campus</option>
              </select>
            </div>

            <div className="col-md-3">
              <label htmlFor="city" className="form-label">
                City
              </label>

              <input
                id="city"
                name="city"
                type="text"
                className="form-control"
                placeholder="Example: San Jose"
                value={filters.city}
                onChange={handleChange}
              />
            </div>

            <div className="col-md-4">
              <label htmlFor="remote" className="form-label">
                Work mode
              </label>

              <select
                id="remote"
                name="remote"
                className="form-select"
                value={filters.remote}
                onChange={handleChange}
              >
                <option value="">All work modes</option>
                <option value="true">Remote</option>
                <option value="false">On-site</option>
              </select>
            </div>

            <div className="col-md-4">
              <label htmlFor="min_salary" className="form-label">
                Minimum salary
              </label>

              <input
                id="min_salary"
                name="min_salary"
                type="number"
                min="0"
                className="form-control"
                placeholder="Example: 25"
                value={filters.min_salary}
                onChange={handleChange}
              />
            </div>

            <div className="col-md-4 d-flex align-items-end gap-2">
              <button type="submit" className="btn btn-primary">
                Search
              </button>

              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={handleReset}
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      </form>

      {loading && <p>Loading jobs...</p>}

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="alert alert-info">
          No matching jobs found.
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <div className="row g-4">
          {jobs.map((job) => (
            <div className="col-md-6" key={job.id}>
              <div className="card h-100 shadow-sm border-0">
                <div className="card-body">
                  <span className="badge bg-primary mb-3">
                    {job.category}
                  </span>

                  <h4 className="card-title">
                    {job.title}
                  </h4>

                  <h6 className="text-muted mb-3">
                    {job.company_name}
                  </h6>

                  <p>
                    <strong>Location:</strong> {job.location}
                  </p>

                  <p>
                    <strong>Work mode:</strong>{" "}
                    {job.is_remote ? "Remote" : "On-site"}
                  </p>

                  <p>
                    <strong>Salary:</strong>{" "}
                    {formatSalary(job)}
                  </p>

                  <p>
                    <strong>Deadline:</strong>{" "}
                    {job.deadline}
                  </p>

                  <Link
                    to={`/student/jobs/${job.id}`}
                    className="btn btn-outline-primary"
                  >
                    View Details
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

export default Jobs;