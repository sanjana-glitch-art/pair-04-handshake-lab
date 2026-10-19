import { useEffect, useState } from "react";
import {
  getEmployerProfile,
  updateEmployerProfile,
  uploadEmployerPicture,
  uploadUrl,
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
  const [picturePath, setPicturePath] = useState("");
  const [uploading, setUploading] = useState(false);

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
      setPicturePath(data.profile_picture_path || "");
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
      // Blank optional fields are sent as null so validation accepts them.
      await updateEmployerProfile({
        ...profile,
        location: profile.location || null,
        description: profile.description || null,
        contact_email: profile.contact_email || null,
        contact_phone: profile.contact_phone || null,
      });
      setMessage("Company profile updated successfully.");
    } catch (err) {
      setError(err.message || "Unable to update profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePictureChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");

    try {
      const updated = await uploadEmployerPicture(file);
      setPicturePath(updated.profile_picture_path || "");
      setMessage("Company picture updated.");
    } catch (err) {
      setError(err.message || "Unable to upload picture.");
    } finally {
      setUploading(false);
      event.target.value = "";
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
          <div className="d-flex align-items-center gap-3 mb-4">
            {picturePath ? (
              <img
                src={uploadUrl(picturePath)}
                alt="Company"
                className="rounded border"
                width="80"
                height="80"
                style={{ objectFit: "cover" }}
              />
            ) : (
              <div
                className="rounded bg-primary-subtle d-flex align-items-center justify-content-center fs-3"
                style={{ width: 80, height: 80 }}
              >
                {(profile.company_name || "?").charAt(0).toUpperCase()}
              </div>
            )}

            <div>
              <label className="btn btn-outline-primary btn-sm mb-1">
                {uploading ? "Uploading..." : "Change picture"}
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  hidden
                  onChange={handlePictureChange}
                  disabled={uploading}
                />
              </label>
              <div className="small text-muted">PNG or JPEG, up to 2 MB.</div>
            </div>
          </div>

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