import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getMyApplications,
  getMyPreferences,
  getMyProfile,
  getEvents,
  searchJobs,
} from "../services/api.js";

function StudentDashboard() {
  const [profile, setProfile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [events, setEvents] = useState([]);
  const [applications, setApplications] = useState([]);
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [
        profileData,
        jobsData,
        eventsData,
        applicationsData,
        preferencesData,
      ] = await Promise.all([
        getMyProfile(),
        searchJobs(),
        getEvents(),
        getMyApplications(),
        getMyPreferences(),
      ]);

      setProfile(profileData);
      setJobs(Array.isArray(jobsData) ? jobsData.slice(0, 3) : []);
      setEvents(
        Array.isArray(eventsData) ? eventsData.slice(0, 3) : []
      );
      setApplications(
        Array.isArray(applicationsData)
          ? applicationsData
          : []
      );
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
    </div>
  );
}

export default StudentDashboard;