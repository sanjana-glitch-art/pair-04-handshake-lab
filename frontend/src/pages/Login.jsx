import { useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
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
      const loginResult = await login(formData);

      if (loginResult.user_role === "company") {
        navigate("/employer/dashboard");
      } else {
        navigate("/student/dashboard");
      }
    } catch (err) {
      setError(
        err.message || "Unable to log in."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleLogin() {
    setError(
      "Google login will be available after Google OAuth is configured."
    );
  }

  return (
    <div className="login-page">
      <main className="login-content">
        <div className="handshake-logo">
          H
        </div>

        <h1>Log in or sign up</h1>

        <button
          type="button"
          className="google-login-button"
          onClick={handleGoogleLogin}
        >
          <span className="google-mark">
            G
          </span>

          Continue with Google
        </button>

        <div className="login-divider">
          <span />
          <small>or</small>
          <span />
        </div>

        {location.state?.message && (
          <div className="alert alert-success">
            {location.state.message}
          </div>
        )}

        {error && (
          <div className="alert alert-danger">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <input
            type="email"
            name="email"
            placeholder="Email"
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
            required
          />

          <button
            type="submit"
            className="email-login-button"
            disabled={loading}
          >
            {loading
              ? "Signing in..."
              : "Continue with email"}
          </button>
        </form>

        <p className="employer-text">
          Hiring? Sign up as an{" "}
          <Link to="/company-signup">
            employer
          </Link>
        </p>

        <p className="team-credit">
          Team 4 · Sanjana and Karthik
        </p>

        <p className="login-signup-link">
          New student?{" "}
          <Link to="/signup">
            Create an account
          </Link>
        </p>
      </main>
    </div>
  );
}

export default Login;