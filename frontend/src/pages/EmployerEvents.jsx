import { useEffect, useState } from "react";
import {
  getEmployerEvents,
  createEmployerEvent,
  updateEmployerEvent,
  deleteEmployerEvent,
} from "../services/api.js";

const emptyForm = {
  event_name: "",
  description: "",
  event_date: "",
  event_time: "",
  location: "",
  eligibility: "",
};

function EmployerEvents() {
  const [events, setEvents] = useState([]);
  const [formData, setFormData] = useState(emptyForm);
  const [editingEventId, setEditingEventId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadEvents();
  }, []);

  async function loadEvents() {
    try {
      const data = await getEmployerEvents();
      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Unable to load events.");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(event) {
    setFormData({
      ...formData,
      [event.target.name]: event.target.value,
    });
  }

  function resetForm() {
    setFormData(emptyForm);
    setEditingEventId(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);

    try {
      if (editingEventId) {
        await updateEmployerEvent(editingEventId, formData);
        setMessage("Event updated successfully.");
      } else {
        await createEmployerEvent(formData);
        setMessage("Event created successfully.");
      }

      resetForm();
      await loadEvents();
    } catch (err) {
      setError(err.message || "Unable to save event.");
    } finally {
      setSaving(false);
    }
  }

  function startEditing(event) {
    setEditingEventId(event.id);

    setFormData({
      event_name: event.event_name || "",
      description: event.description || "",
      event_date: event.event_date || "",
      event_time: event.event_time || "",
      location: event.location || "",
      eligibility: event.eligibility || "",
    });
  }

  async function handleDelete(eventId) {
    if (!window.confirm("Delete this event?")) {
      return;
    }

    try {
      await deleteEmployerEvent(eventId);
      setMessage("Event deleted successfully.");
      await loadEvents();
    } catch (err) {
      setError(err.message || "Unable to delete event.");
    }
  }

  return (
    <div className="container py-5">
      <h1>Manage Events</h1>
      <p className="text-muted">
        Create and manage your career events.
      </p>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="card shadow-sm mb-5">
        <div className="card-body">
          <h4>
            {editingEventId ? "Edit Event" : "Create an Event"}
          </h4>

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Event name</label>
              <input
                type="text"
                name="event_name"
                className="form-control"
                value={formData.event_name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Description</label>
              <textarea
                name="description"
                className="form-control"
                rows="4"
                value={formData.description}
                onChange={handleChange}
                required
              />
            </div>

            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label">Event date</label>
                <input
                  type="date"
                  name="event_date"
                  className="form-control"
                  value={formData.event_date}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="col-md-6 mb-3">
                <label className="form-label">Event time</label>
                <input
                  type="time"
                  name="event_time"
                  className="form-control"
                  value={formData.event_time}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="mb-3">
              <label className="form-label">Location</label>
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

            <div className="mb-3">
              <label className="form-label">
                Eligibility
              </label>
              <input
                type="text"
                name="eligibility"
                className="form-control"
                value={formData.eligibility}
                onChange={handleChange}
                placeholder="Computer Science students"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary me-2"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : editingEventId
                  ? "Update Event"
                  : "Create Event"}
            </button>

            {editingEventId && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={resetForm}
              >
                Cancel
              </button>
            )}
          </form>
        </div>
      </div>

      <h3>Your Events</h3>

      {loading ? (
        <p>Loading events...</p>
      ) : events.length === 0 ? (
        <div className="alert alert-info">
          You have not created any events yet.
        </div>
      ) : (
        <div className="row g-4">
          {events.map((event) => (
            <div className="col-md-6" key={event.id}>
              <div className="card h-100 shadow-sm">
                <div className="card-body">
                  <h5>{event.event_name}</h5>

                  <p>{event.description}</p>

                  <p>
                    <strong>Date:</strong>{" "}
                    {event.event_date}
                  </p>

                  <p>
                    <strong>Time:</strong>{" "}
                    {event.event_time}
                  </p>

                  <p>
                    <strong>Location:</strong>{" "}
                    {event.location}
                  </p>

                  <button
                    className="btn btn-outline-primary btn-sm me-2"
                    onClick={() => startEditing(event)}
                  >
                    Edit
                  </button>

                  <button
                    className="btn btn-outline-danger btn-sm"
                    onClick={() => handleDelete(event.id)}
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

export default EmployerEvents;