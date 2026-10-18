import { useEffect, useState } from "react";
import {
  getMyPreferences,
  updateMyPreferences,
} from "../services/api.js";

const emptyPreferences = {
  preferred_city: "",
  preferred_category: "",
  minimum_salary: "",
  preferred_work_mode: "",
  preferred_major: "",
  preferred_event_major: "",
};

function Preferences() {
  const [preferences, setPreferences] = useState(
    emptyPreferences
  );

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadPreferences() {
      try {
        setLoading(true);
        setError("");

        const data = await getMyPreferences();

        setPreferences({
          preferred_city: data.preferred_city || "",
          preferred_category: data.preferred_category || "",
          minimum_salary:
            data.minimum_salary ?? "",
          preferred_work_mode:
            data.preferred_work_mode || "",
          preferred_major:
            data.preferred_major || "",
          preferred_event_major:
            data.preferred_event_major || "",
        });
      } catch (err) {
        setError(
          err.message || "Unable to load preferences."
        );
      } finally {
        setLoading(false);
      }
    }

    loadPreferences();
  }, []);

  function handleChange(event) {
    const { name, value } = event.target;

    setPreferences((previousPreferences) => ({
      ...previousPreferences,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const payload = {
        preferred_city:
          preferences.preferred_city || null,

        preferred_category:
          preferences.preferred_category || null,

        minimum_salary:
          preferences.minimum_salary === ""
            ? null
            : Number(preferences.minimum_salary),

        preferred_work_mode:
          preferences.preferred_work_mode || null,

        preferred_major:
          preferences.preferred_major || null,

        preferred_event_major:
          preferences.preferred_event_major || null,
      };

      const updated = await updateMyPreferences(payload);

      setPreferences({
        preferred_city: updated.preferred_city || "",
        preferred_category:
          updated.preferred_category || "",
        minimum_salary:
          updated.minimum_salary ?? "",
        preferred_work_mode:
          updated.preferred_work_mode || "",
        preferred_major:
          updated.preferred_major || "",
        preferred_event_major:
          updated.preferred_event_major || "",
      });

      setSuccess("Preferences saved successfully.");
    } catch (err) {
      setError(
        err.message || "Unable to save preferences."
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="container py-5">
        <p>Loading preferences...</p>
      </div>
    );
  }

  return (
    <div className="container py-5">
      <div className="card shadow-sm border-0">
        <div className="card-body p-4">
          <h1>My Preferences</h1>

          <p className="text-muted">
            Save your preferences so we can provide more relevant job
            and event recommendations.
          </p>

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

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label
                htmlFor="preferred_city"
                className="form-label"
              >
                Preferred city
              </label>

              <select
                id="preferred_city"
                name="preferred_city"
                className="form-select"
                value={preferences.preferred_city}
                onChange={handleChange}
              >
                <option value="">Any city</option>
                <option value="San Jose">San Jose</option>
                <option value="Santa Clara">
                  Santa Clara
                </option>
                <option value="Milpitas">Milpitas</option>
              </select>
            </div>

            <div className="mb-3">
              <label
                htmlFor="preferred_category"
                className="form-label"
              >
                Preferred job category
              </label>

              <select
                id="preferred_category"
                name="preferred_category"
                className="form-select"
                value={preferences.preferred_category}
                onChange={handleChange}
              >
                <option value="">Any category</option>
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

            <div className="mb-3">
              <label
                htmlFor="minimum_salary"
                className="form-label"
              >
                Minimum salary
              </label>

              <input
                id="minimum_salary"
                name="minimum_salary"
                type="number"
                min="0"
                className="form-control"
                placeholder="Example: 25"
                value={preferences.minimum_salary}
                onChange={handleChange}
              />
            </div>

            <div className="mb-3">
              <label
                htmlFor="preferred_work_mode"
                className="form-label"
              >
                Preferred work mode
              </label>

              <select
                id="preferred_work_mode"
                name="preferred_work_mode"
                className="form-select"
                value={preferences.preferred_work_mode}
                onChange={handleChange}
              >
                <option value="">Any work mode</option>
                <option value="remote">Remote</option>
                <option value="onsite">On-site</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>

            <div className="mb-3">
              <label
                htmlFor="preferred_major"
                className="form-label"
              >
                Preferred job major
              </label>

              <input
                id="preferred_major"
                name="preferred_major"
                type="text"
                className="form-control"
                placeholder="Example: Data Science"
                value={preferences.preferred_major}
                onChange={handleChange}
              />
            </div>

            <div className="mb-4">
              <label
                htmlFor="preferred_event_major"
                className="form-label"
              >
                Preferred event area
              </label>

              <input
                id="preferred_event_major"
                name="preferred_event_major"
                type="text"
                className="form-control"
                placeholder="Example: Technology"
                value={preferences.preferred_event_major}
                onChange={handleChange}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Preferences"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Preferences;