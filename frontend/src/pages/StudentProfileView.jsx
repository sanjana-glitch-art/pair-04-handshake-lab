import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorMessage from "../components/ErrorMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getStudentProfile, uploadUrl } from "../services/api.js";
import { initials } from "./Students.jsx";

// Read-only student profile, opened from the directory or from an
// employer's applicant / registrant lists.
function StudentProfileView({ backTo = "/student/students", backLabel = "Students" }) {
  const { studentId } = useParams();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");

    getStudentProfile(studentId)
      .then(setStudent)
      .catch((err) => setError(err.message || "Could not load this profile."))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error || !student) {
    return <ErrorMessage message={error || "Student not found."} />;
  }

  const rows = [
    ["College", student.college],
    ["Degree", [student.degree, student.major].filter(Boolean).join(" ")],
    ["Graduation year", student.graduation_year],
    ["CGPA", student.cgpa],
    ["Location", [student.city, student.state, student.country].filter(Boolean).join(", ")],
    ["Email", student.email],
    ["Phone", student.phone],
  ];

  return (
    <div className="container-fluid py-3" style={{ maxWidth: 860 }}>
      <Link to={backTo} className="small">
        ← {backLabel}
      </Link>

      <div className="card mt-3">
        <div className="card-body">
          <div className="d-flex align-items-center gap-3 mb-3">
            {student.profile_picture_path ? (
              <img
                src={uploadUrl(student.profile_picture_path)}
                alt=""
                className="rounded-circle"
                width="72"
                height="72"
                style={{ objectFit: "cover" }}
              />
            ) : (
              <div
                className="rounded-circle bg-primary-subtle d-flex align-items-center justify-content-center fs-4 fw-semibold"
                style={{ width: 72, height: 72 }}
              >
                {initials(student.full_name)}
              </div>
            )}
            <div>
              <h1 className="h4 mb-0">{student.full_name}</h1>
              <div className="text-muted">{student.major}</div>
            </div>
          </div>

          {student.career_objective && (
            <>
              <h2 className="h6 mt-3">Career objective</h2>
              <p>{student.career_objective}</p>
            </>
          )}

          <dl className="row mb-0">
            {rows.map(([label, value]) =>
              value ? (
                <div className="col-sm-6 mb-2" key={label}>
                  <dt className="small text-muted">{label}</dt>
                  <dd className="mb-0">{value}</dd>
                </div>
              ) : null
            )}
          </dl>

          {student.experience && (
            <>
              <h2 className="h6 mt-3">Experience</h2>
              <p className="mb-0">{student.experience}</p>
            </>
          )}

          <h2 className="h6 mt-3">Skills</h2>
          <div className="d-flex flex-wrap gap-1">
            {student.skills.length === 0 ? (
              <span className="text-muted small">No skills listed.</span>
            ) : (
              student.skills.map((skill) => (
                <span key={skill} className="badge text-bg-light border">
                  {skill}
                </span>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StudentProfileView;
