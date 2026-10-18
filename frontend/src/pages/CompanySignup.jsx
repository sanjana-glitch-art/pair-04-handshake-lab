import { useState } from "react";
import {
  Link,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function CompanySignup() {
  const navigate = useNavigate();
  const { companySignup } = useAuth();

  const [formData, setFormData] = useState({
    company_name: "",
    email: "",
    password: "",
    location: "",
    description: "",
    contact_email: "",
    contact_phone: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    setFormData((previous) => ({
      ...previous,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await companySignup({
        ...formData,
        location: formData.location || null,
        description: formData.description || null,
        contact_email: formData.contact_email || null,
        contact_phone: formData.contact_phone || null,
      });

      navigate("/login", {
        state: {
          message:
            "Company account created successfully. Please log in.",
        },
      });
    } catch (err) {
      setError(
        err.message ||
          "Unable to create company account."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <main className="login-content company-signup-content">
        <div className="handshake-logo">
          H
        </div>

        <h1>Create company account</h1>

        <p className="text-muted">
          Post jobs, create events, and connect with students.
        </p>

        {error && (
          <div className="alert alert-danger">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            name="company_name"
            placeholder="Company name"
            value={formData.company_name}
            onChange={handleChange}
            required
          />

          <input
            type="email"
            name="email"
            placeholder="Company login email"
            value={formData.email}
            onChange={handleChange}
            required
          />

          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
            minLength="8"
            required
          />

          <input
            type="text"
            name="location"
            placeholder="Company location"
            value={formData.location}
            onChange={handleChange}
          />

          <textarea
            name="description"
            placeholder="Company description"
            value={formData.description}
            onChange={handleChange}
            rows="4"
          />

          <input
            type="email"
            name="contact_email"
            placeholder="Contact email (optional)"
            value={formData.contact_email}
            onChange={handleChange}
          />

          <input
            type="text"
            name="contact_phone"
            placeholder="Contact phone (optional)"
            value={formData.contact_phone}
            onChange={handleChange}
          />

          <button
            type="submit"
            className="email-login-button"
            disabled={loading}
          >
            {loading
              ? "Creating account..."
              : "Create company account"}
          </button>
        </form>

        <p className="login-signup-link">
          Already have an account?{" "}
          <Link to="/login">
            Log in
          </Link>
        </p>

        <p className="team-credit">
          Team 4 · Sanjana and Karthik
        </p>
      </main>
    </div>
  );
}

export default CompanySignup;