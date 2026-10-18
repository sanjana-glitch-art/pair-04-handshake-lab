import { useEffect, useState } from "react";
import {
  getEmployerProfile,
  updateEmployerProfile,
} from "../services/api.js";

const emptyProfile = {
  company_name: "",
  location: "",
  description: "",
  contact_email: "",
  contact_phone: "",
};

function EmployerProfile() {
  const [profile, setProfile] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      const data = await getEmployerProfile();

      setProfile({
        company_name: data.company_name || "",
        location: data.location || "",
        description: data.description || "",
        contact_email: data.contact_email || "",
        contact_phone: data.contact_phone || "",
      });
    } catch (err) {
      setError(err.message || "Unable to load profile.");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(event) {
    setProfile({
      ...profile,
      [event.target.name]: event.target.value,
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await updateEmployerProfile(profile);
      setMessage("Company profile updated successfully.");
    } catch (err) {
      setError(err.message || "Unable to update profile.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="container py-5">
        <p>Loading company profile...</p>
      </div>
    );
  }

  return (
    <div className="container py-5">
      <div className="mb-4">
        <p className="employer-eyebrow">
          COMPANY PROFILE
        </p>

        <h1>Company profile</h1>

        <p className="text-muted">
          Keep your company information updated for students.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {message && (
        <div className="alert alert-success">
          {message}
        </div>
      )}

      <div className="card shadow-sm">
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">
                Company name
              </label>

              <input
                type="text"
                name="company_name"
                className="form-control"
                value={profile.company_name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">
                Location
              </label>

              <input
                type="text"
                name="location"
                className="form-control"
                value={profile.location}
                onChange={handleChange}
                placeholder="San Jose, California"
              />
            </div>

            <div className="mb-3">
              <label className="form-label">
                Company description
              </label>

              <textarea
                name="description"
                className="form-control"
                rows="5"
                value={profile.description}
                onChange={handleChange}
                placeholder="Tell students about your company."
              />
            </div>

            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label">
                  Contact email
                </label>

                <input
                  type="email"
                  name="contact_email"
                  className="form-control"
                  value={profile.contact_email}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-6 mb-3">
                <label className="form-label">
                  Contact phone
                </label>

                <input
                  type="text"
                  name="contact_phone"
                  className="form-control"
                  value={profile.contact_phone}
                  onChange={handleChange}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? "Saving..." : "Save profile"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default EmployerProfile;