import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getEvents,
  registerForEvent,
} from "../services/api.js";

function Events() {
  const [events, setEvents] = useState([]);
  const [filters, setFilters] = useState({
    search: "",
    city: "",
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadEvents(currentFilters = {}) {
    try {
      setLoading(true);
      setError("");

      const data = await getEvents(currentFilters);

      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Unable to load events.");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents({});
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
    loadEvents(filters);
  }

  function handleReset() {
    const emptyFilters = {
      search: "",
      city: "",
    };

    setFilters(emptyFilters);
    loadEvents(emptyFilters);
  }

  async function handleRegister(eventId) {
    try {
      setError("");
      setMessage("");

      const result = await registerForEvent(eventId);

      setMessage(
        result.message || "Successfully registered for the event."
      );
      setEvents((current) =>
        current.map((item) =>
          item.id === eventId ? { ...item, is_registered: true } : item
        )
      );
    } catch (err) {
      setError(err.message || "Unable to register for the event.");
    }
  }

  // Event dates are calendar dates; parse them as local time so
  // they do not shift a day in US time zones.
  function formatDate(value) {
    return new Date(`${value}T00:00:00`).toLocaleDateString();
  }

  function formatTime(value) {
    return value?.slice(0, 5) || "Time not available";
  }

  return (
    <div className="container py-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1>Career Events</h1>

          <p className="text-muted">
            Discover networking events, workshops, and career opportunities.
          </p>
        </div>

        <Link
          to="/student/registered-events"
          className="btn btn-outline-primary"
        >
          Registered Events
        </Link>
      </div>

      <form
        onSubmit={handleSubmit}
        className="card shadow-sm border-0 mb-4"
      >
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <label
                htmlFor="search"
                className="form-label"
              >
                Search events
              </label>

              <input
                id="search"
                name="search"
                type="text"
                className="form-control"
                placeholder="Search by event name"
                value={filters.search}
                onChange={handleChange}
              />
            </div>

            <div className="col-md-4">
              <label
                htmlFor="city"
                className="form-label"
              >
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

            <div className="col-md-2 d-flex align-items-end gap-2">
              <button
                type="submit"
                className="btn btn-primary"
              >
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

      {message && (
        <div className="alert alert-success">
          {message}
        </div>
      )}

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {loading && <p>Loading events...</p>}

      {!loading && !error && events.length === 0 && (
        <div className="alert alert-info">
          No upcoming events found.
        </div>
      )}

      {!loading && events.length > 0 && (
        <div className="row g-4">
          {events.map((event) => (
            <div
              className="col-md-6"
              key={event.id}
            >
              <div className="card h-100 shadow-sm border-0">
                <div className="card-body">
                  <span className="badge bg-primary mb-3">
                    Career Event
                  </span>

                  <h4>{event.event_name}</h4>

                  <h6 className="text-muted mb-3">
                    Hosted by {event.company_name}
                  </h6>

                  <p>{event.description}</p>

                  <p className="mb-2">
                    <strong>Date:</strong>{" "}
                    {formatDate(event.event_date)}
                  </p>

                  <p className="mb-2">
                    <strong>Time:</strong>{" "}
                    {formatTime(event.event_time)}
                  </p>

                  <p className="mb-2">
                    <strong>Location:</strong>{" "}
                    {event.location}
                  </p>

                  <p className="mb-3">
                    <strong>Eligibility:</strong>{" "}
                    {event.eligibility || "Open to students"}
                  </p>

                  {event.is_registered ? (
                    <span className="badge text-bg-success">Registered</span>
                  ) : event.is_eligible === false ? (
                    <button type="button" className="btn btn-secondary" disabled>
                      Not eligible
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleRegister(event.id)}
                    >
                      Register
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Events;