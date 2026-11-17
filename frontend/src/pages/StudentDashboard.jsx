import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { getMyPreferences, getMyProfile } from "../services/api.js";
import { fetchMyApplications, selectApplications } from "../store/slices/applicationsSlice.js";
import { fetchEvents, selectEvents } from "../store/slices/eventsSlice.js";
import { searchJobs, selectJobResults } from "../store/slices/jobsSlice.js";
import { fetchSavedItems, removeSavedItem, selectSavedItems } from "../store/slices/savedSlice.js";

function StudentDashboard() {
  const dispatch = useDispatch();
  const [profile, setProfile] = useState(null);
  const jobs = useSelector(selectJobResults).slice(0, 3);
  const events = useSelector(selectEvents).slice(0, 3);
  const applications = useSelector(selectApplications);
  const savedItems = useSelector(selectSavedItems);
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [profileData, preferencesData] = await Promise.all([
        getMyProfile(),
        getMyPreferences(),
        dispatch(searchJobs({})),
        dispatch(fetchEvents({})),
        dispatch(fetchMyApplications("")),
        dispatch(fetchSavedItems()),
      ]);

      setProfile(profileData);
      setPreferences(preferencesData);
    } catch (error) {
      console.error("Dashboard loading failed:", error);
    } finally {
      setLoading(false);
    }
  }

  const studentName =
    profile?.full_name?.split(" ")[0] || "Student";

  const profileComplete = Boolean(
    profile?.full_name &&
      profile?.college &&
      profile?.major
  );

  const resumeComplete = applications.length > 0;

  const preferencesComplete = Boolean(
    preferences &&
      (
        preferences.preferred_city ||
        preferences.preferred_category ||
        preferences.preferred_major ||
        preferences.preferred_work_mode
      )
  );

  function formatDate(value) {
    if (!value) {
      return "";
    }

    return new Date(value).toLocaleDateString(
      "en-US",
      {
        month: "short",
        day: "numeric",
        year: "numeric",
      }
    );
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-heading">
        <h1>Welcome back, {studentName}</h1>

        <p>
          Find opportunities, build your profile, and grow your
          career.
        </p>
      </div>

      <section className="search-ready-card">
        <div>
          <h2>Get search-ready</h2>

          <p>
            Complete these steps to get matched with the right
            opportunities.
          </p>
        </div>

        {loading ? (
          <p className="text-muted">
            Checking your progress...
          </p>
        ) : (
          <div className="checklist">
            <div
              className={
                resumeComplete
                  ? "checklist-item completed"
                  : "checklist-item"
              }
            >
              <span className="checklist-circle">
                {resumeComplete ? "✓" : ""}
              </span>
              Upload a resume
            </div>

            <div
              className={
                profileComplete
                  ? "checklist-item completed"
                  : "checklist-item"
              }
            >
              <span className="checklist-circle">
                {profileComplete ? "✓" : ""}
              </span>
              Complete your profile
            </div>

            <div
              className={
                preferencesComplete
                  ? "checklist-item completed"
                  : "checklist-item"
              }
            >
              <span className="checklist-circle">
                {preferencesComplete ? "✓" : ""}
              </span>
              Review your job search preferences
            </div>
          </div>
        )}
      </section>

      <h2 className="section-heading">
        Level up your skills
      </h2>

      <section className="ai-banner">
        <div className="ai-orb">✦</div>

        <div>
          <h3>Introducing AI Skills Studio</h3>

          <p>
            Build projects with AI to gain relevant experience
            for your career path.
          </p>
        </div>

        <Link to="/student/assistant">
          Start building
        </Link>
      </section>

      <div className="jobs-heading-row">
        <h2 className="section-heading">
          Top jobs for you
        </h2>

        <Link
          to="/student/jobs"
          className="view-all-link"
        >
          View all →
        </Link>
      </div>

      <section className="dashboard-job-grid">
        {jobs.length === 0 ? (
          <p className="text-muted">
            No jobs available right now.
          </p>
        ) : (
          jobs.map((job) => (
            <Link
              to={`/student/jobs/${job.id}`}
              className="dashboard-job-card"
              key={job.id}
            >
              <div className="company-square">
                {job.company_name
                  ? job.company_name
                      .slice(0, 2)
                      .toUpperCase()
                  : "CO"}
              </div>

              <div>
                <h4>{job.title}</h4>

                <p>{job.company_name}</p>

                <small>
                  {job.location}
                  {job.is_remote ? " · Remote" : ""}
                </small>
              </div>

              <span className="bookmark">♡</span>
            </Link>
          ))
        )}
      </section>

      <div className="jobs-heading-row events-heading-row">
        <h2 className="section-heading">
          Top events
        </h2>

        <Link
          to="/student/events"
          className="view-all-link"
        >
          View all →
        </Link>
      </div>

      <section className="dashboard-event-grid">
        {events.length === 0 ? (
          <p className="text-muted">
            No upcoming events available.
          </p>
        ) : (
          events.map((event) => (
            <Link
              to="/student/events"
              className="dashboard-event-card"
              key={event.id}
            >
              <div className="event-date-box">
                <strong>
                  {event.event_date
                    ? new Date(
                        event.event_date
                      ).toLocaleDateString(
                        "en-US",
                        { day: "2-digit" }
                      )
                    : "--"}
                </strong>

                <span>
                  {event.event_date
                    ? new Date(
                        event.event_date
                      ).toLocaleDateString(
                        "en-US",
                        { month: "short" }
                      )
                    : ""}
                </span>
              </div>

              <div>
                <h4>{event.event_name}</h4>

                <p>{event.location}</p>

                <small>
                  {event.company_name}
                </small>
              </div>
            </Link>
          ))
        )}
      </section>

      <h2 className="section-heading mt-4">Saved items</h2>

      <section className="card p-3" data-testid="saved-items">
        {savedItems.length === 0 ? (
          <p className="text-muted mb-0">
            Nothing saved yet. Save a job from the Jobs page or ask the assistant to save one.
          </p>
        ) : (
          <ul className="list-unstyled mb-0">
            {savedItems.map((item) => (
              <li key={item.id} className="d-flex justify-content-between align-items-center py-1">
                <span>
                  <span className="badge bg-secondary me-2">{item.item_type}</span>
                  {item.item_type === "job" ? (
                    <Link to={`/student/jobs/${item.item_id}`}>{item.title}</Link>
                  ) : (
                    item.title
                  )}
                </span>
                <button
                  type="button"
                  className="btn btn-link btn-sm text-danger"
                  onClick={() => dispatch(removeSavedItem(item.id))}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default StudentDashboard;