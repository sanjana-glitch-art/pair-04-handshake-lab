import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import StudentLayout from "./layouts/StudentLayout.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";

function PlaceholderPage({ title }) {
  return (
    <div className="container py-4">
      <h2>{title}</h2>
      <p className="text-muted">
        This student feature will be implemented next.
      </p>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Redirect the home page to the student dashboard */}
        <Route
          path="/"
          element={<Navigate to="/student/dashboard" replace />}
        />

        {/* Public authentication pages */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Student application pages */}
        <Route path="/student" element={<StudentLayout />}>
          <Route path="dashboard" element={<StudentDashboard />} />

          <Route
            path="profile"
            element={<PlaceholderPage title="My Profile" />}
          />

          <Route
            path="jobs"
            element={<PlaceholderPage title="Find Jobs" />}
          />

          <Route
            path="jobs/:jobId"
            element={<PlaceholderPage title="Job Details" />}
          />

          <Route
            path="applications"
            element={<PlaceholderPage title="My Applications" />}
          />

          <Route
            path="events"
            element={<PlaceholderPage title="Find Events" />}
          />

          <Route
            path="events/registered"
            element={<PlaceholderPage title="Registered Events" />}
          />

          <Route
            path="students"
            element={<PlaceholderPage title="Browse Students" />}
          />

          <Route
            path="assistant"
            element={<PlaceholderPage title="AI Assistant" />}
          />
        </Route>

        {/* Page shown for unknown URLs */}
        <Route
          path="*"
          element={<PlaceholderPage title="Page Not Found" />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;