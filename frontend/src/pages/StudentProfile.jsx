import { useEffect, useState } from "react";

import {
  getMyProfile,
  updateMyProfile,
} from "../services/api.js";


const emptyProfile = {
  email: "",
  full_name: "",
  date_of_birth: "",
  city: "",
  state: "",
  country: "",
  career_objective: "",
  college: "",
  degree: "",
  major: "",
  graduation_year: "",
  cgpa: "",
  experience: "",
  phone: "",
};


function StudentProfile() {
  const [profile, setProfile] = useState(emptyProfile);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");


  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await getMyProfile();

        /*
          data may be undefined if the request fails unexpectedly.
          Using data || {} prevents errors such as:
          "Cannot read properties of undefined"
        */
        const safeData = data || {};

        setProfile({
          ...emptyProfile,
          ...safeData,

          date_of_birth: safeData.date_of_birth || "",
          graduation_year: safeData.graduation_year || "",
          cgpa: safeData.cgpa || "",
        });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, []);


  function handleChange(event) {
    const { name, value } = event.target;

    setProfile((currentProfile) => ({
      ...currentProfile,
      [name]: value,
    }));
  }


  async function handleSubmit(event) {
    event.preventDefault();

    setSaving(true);
    setMessage("");
    setError("");

    try {
      const profileData = {
        ...profile,

        date_of_birth:
          profile.date_of_birth || null,

        graduation_year:
          profile.graduation_year
            ? Number(profile.graduation_year)
            : null,

        cgpa:
          profile.cgpa
            ? Number(profile.cgpa)
            : null,
      };

      const updatedProfile =
        await updateMyProfile(profileData);

      const safeUpdatedProfile =
        updatedProfile || profileData;

      setProfile({
        ...emptyProfile,
        ...safeUpdatedProfile,

        date_of_birth:
          safeUpdatedProfile.date_of_birth || "",

        graduation_year:
          safeUpdatedProfile.graduation_year || "",

        cgpa:
          safeUpdatedProfile.cgpa || "",
      });

      setMessage(
        "Profile updated successfully."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }


  if (loading) {
    return (
      <div className="container py-5">
        <p>Loading profile...</p>
      </div>
    );
  }


  return (
    <div className="container py-5">
      <div className="row justify-content-center">
        <div className="col-lg-9">
          <div className="card shadow-sm border-0">
            <div className="card-body p-4">
              <h2 className="mb-2">
                My Profile
              </h2>

              <p className="text-muted mb-4">
                Keep your information updated
                for better opportunities.
              </p>

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

              <form onSubmit={handleSubmit}>
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Full name
                    </label>

                    <input
                      type="text"
                      name="full_name"
                      className="form-control"
                      value={profile.full_name}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Email
                    </label>

                    <input
                      type="email"
                      name="email"
                      className="form-control"
                      value={profile.email}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Date of birth
                    </label>

                    <input
                      type="date"
                      name="date_of_birth"
                      className="form-control"
                      value={profile.date_of_birth}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Phone
                    </label>

                    <input
                      type="tel"
                      name="phone"
                      className="form-control"
                      value={profile.phone}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      College
                    </label>

                    <input
                      type="text"
                      name="college"
                      className="form-control"
                      value={profile.college}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Degree
                    </label>

                    <input
                      type="text"
                      name="degree"
                      className="form-control"
                      value={profile.degree}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Major
                    </label>

                    <input
                      type="text"
                      name="major"
                      className="form-control"
                      value={profile.major}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Graduation year
                    </label>

                    <input
                      type="number"
                      name="graduation_year"
                      className="form-control"
                      value={profile.graduation_year}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      CGPA
                    </label>

                    <input
                      type="number"
                      name="cgpa"
                      className="form-control"
                      step="0.01"
                      min="0"
                      max="4"
                      value={profile.cgpa}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      City
                    </label>

                    <input
                      type="text"
                      name="city"
                      className="form-control"
                      value={profile.city}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      State
                    </label>

                    <input
                      type="text"
                      name="state"
                      className="form-control"
                      value={profile.state}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Country
                    </label>

                    <input
                      type="text"
                      name="country"
                      className="form-control"
                      value={profile.country}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-12 mb-3">
                    <label className="form-label">
                      Career objective
                    </label>

                    <textarea
                      name="career_objective"
                      className="form-control"
                      rows="3"
                      value={
                        profile.career_objective
                      }
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-12 mb-4">
                    <label className="form-label">
                      Experience
                    </label>

                    <textarea
                      name="experience"
                      className="form-control"
                      rows="4"
                      value={profile.experience}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-12">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={saving}
                    >
                      {saving
                        ? "Saving..."
                        : "Save Profile"}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


export default StudentProfile;