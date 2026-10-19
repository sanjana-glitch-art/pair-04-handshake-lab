import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRegisteredEvents } from "../services/api.js";

function RegisteredEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadRegisteredEvents() {
      try {
        setLoading(true);
        setError("");

        const data = await getRegisteredEvents();

        setEvents(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(
          err.message || "Unable to load registered events."
        );
      } finally {
        setLoading(false);
      }
    }

    loadRegisteredEvents();
  }, []);

  function formatDate(value) {
    return new Date(`${value}T00:00:00`).toLocaleDateString();
  }

  function formatTime(value) {
    return value?.slice(0, 5) || "Time not available";
  }

  return (
    <div className="container py-5">
      <Link
        to="/student/events"
        className="btn btn-link px-0 mb-3"
      >
        ← Back to Events
      </Link>

      <h1>Registered Events</h1>

      <p className="text-muted mb-4">
        Events you have registered for.
      </p>

      {loading && <p>Loading registered events...</p>}

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {!loading && !error && events.length === 0 && (
        <div className="alert alert-info">
          You have not registered for any events yet.
        </div>
      )}

      {!loading && !error && events.length > 0 && (
        <div className="row g-4">
          {events.map((event) => (
            <div
              className="col-md-6"
              key={event.id}
            >
              <div className="card h-100 shadow-sm border-0">
                <div className="card-body">
                  <span className="badge bg-success mb-3">
                    Registered
                  </span>

                  <h4>{event.event_name}</h4>

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

                  <p className="text-muted">
                    Registered on{" "}
                    {formatDate(event.registered_at)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RegisteredEvents;