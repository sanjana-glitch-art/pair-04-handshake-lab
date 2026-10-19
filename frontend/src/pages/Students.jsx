import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorMessage from "../components/ErrorMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import {
  getStudentMajors,
  searchStudents,
  uploadUrl,
} from "../services/api.js";

const emptyFilters = {
  name: "",
  college: "",
  major: "",
  skill: "",
};

export function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

// Shared by students (browse classmates) and companies (Students tab).
// Companies also get the skillset filter; profileBase is where a card links.
function Students({ profileBase = "/student/students", showSkillFilter = false }) {
  const [filters, setFilters] = useState(emptyFilters);
  const [students, setStudents] = useState([]);
  const [majors, setMajors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(activeFilters) {
    setLoading(true);
    setError("");

    try {
      setStudents(await searchStudents(activeFilters));
    } catch (err) {
      setError(err.message || "Could not load students.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(emptyFilters);
    getStudentMajors().then(setMajors).catch(() => setMajors([]));
  }, []);

  function handleChange(event) {
    setFilters({ ...filters, [event.target.name]: event.target.value });
  }

  function handleSubmit(event) {
    event.preventDefault();
    load(filters);
  }

  function handleReset() {
    setFilters(emptyFilters);
    load(emptyFilters);
  }

  return (
    <div className="container-fluid py-3">
      <h1 className="h3 mb-1">Students</h1>
      <p className="text-muted mb-4">
        {showSkillFilter
          ? "Search students by name, college, major, or skill."
          : "Browse enrolled students by name or college, and filter by major."}
      </p>

      <form className="card card-body mb-4" onSubmit={handleSubmit}>
        <div className="row g-2 align-items-end">
          <div className="col-md-3">
            <label className="form-label small" htmlFor="student-name">Name</label>
            <input
              id="student-name"
              className="form-control"
              name="name"
              value={filters.name}
              onChange={handleChange}
              placeholder="e.g. Maya"
            />
          </div>

          <div className="col-md-3">
            <label className="form-label small" htmlFor="student-college">College</label>
            <input
              id="student-college"
              className="form-control"
              name="college"
              value={filters.college}
              onChange={handleChange}
              placeholder="e.g. San Jose State"
            />
          </div>

          <div className="col-md-2">
            <label className="form-label small" htmlFor="student-major">Major</label>
            <select
              id="student-major"
              className="form-select"
              name="major"
              value={filters.major}
              onChange={handleChange}
            >
              <option value="">All majors</option>
              {majors.map((major) => (
                <option key={major} value={major}>
                  {major}
                </option>
              ))}
            </select>
          </div>

          {showSkillFilter && (
            <div className="col-md-2">
              <label className="form-label small" htmlFor="student-skill">Skill</label>
              <input
                id="student-skill"
                className="form-control"
                name="skill"
                value={filters.skill}
                onChange={handleChange}
                placeholder="e.g. Python"
              />
            </div>
          )}

          <div className="col-md-2 d-flex gap-2">
            <button className="btn btn-primary flex-fill" type="submit">
              Search
            </button>
            <button
              className="btn btn-outline-secondary"
              type="button"
              onClick={handleReset}
            >
              Reset
            </button>
          </div>
        </div>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <LoadingSpinner />
      ) : students.length === 0 ? (
        <p className="text-muted">No students match these filters.</p>
      ) : (
        <div className="row g-3">
          {students.map((student) => (
            <div className="col-md-6 col-lg-4" key={student.user_id}>
              <Link
                to={`${profileBase}/${student.user_id}`}
                className="card h-100 text-decoration-none text-reset"
              >
                <div className="card-body d-flex gap-3">
                  {student.profile_picture_path ? (
                    <img
                      src={uploadUrl(student.profile_picture_path)}
                      alt=""
                      className="rounded-circle"
                      width="48"
                      height="48"
                      style={{ objectFit: "cover", flex: "0 0 48px" }}
                    />
                  ) : (
                    <div
                      className="rounded-circle bg-primary-subtle d-flex align-items-center justify-content-center fw-semibold"
                      style={{ width: 48, height: 48, flex: "0 0 48px" }}
                    >
                      {initials(student.full_name)}
                    </div>
                  )}

                  <div>
                    <div className="fw-semibold">{student.full_name}</div>
                    <div className="small text-muted">
                      {[student.degree, student.major].filter(Boolean).join(" ")}
                      {student.graduation_year ? ` · ${student.graduation_year}` : ""}
                    </div>
                    <div className="small text-muted">{student.college}</div>
                    <div className="mt-2 d-flex flex-wrap gap-1">
                      {student.skills.slice(0, 5).map((skill) => (
                        <span key={skill} className="badge text-bg-light border">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Students;
