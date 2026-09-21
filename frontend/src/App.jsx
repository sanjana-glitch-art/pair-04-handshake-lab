import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import StudentLayout from "./layouts/StudentLayout.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import StudentProfile from "./pages/StudentProfile.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";


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
        <Route
          path="/"
          element={
            <Navigate
              to="/student/dashboard"
              replace
            />
          }
        />

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/signup"
          element={<Signup />}
        />

        <Route element={<ProtectedRoute />}>
          <Route
            path="/student"
            element={<StudentLayout />}
          >
            <Route
              path="dashboard"
              element={<StudentDashboard />}
            />

            <Route
              path="profile"
              element={<StudentProfile />}
            />

            <Route
              path="jobs"
              element={
                <PlaceholderPage title="Find Jobs" />
              }
            />

            <Route
              path="applications"
              element={
                <PlaceholderPage title="My Applications" />
              }
            />

            <Route
              path="events"
              element={
                <PlaceholderPage title="Find Events" />
              }
            />

            <Route
              path="students"
              element={
                <PlaceholderPage title="Browse Students" />
              }
            />

            <Route
              path="assistant"
              element={
                <PlaceholderPage title="AI Assistant" />
              }
            />
          </Route>
        </Route>

        <Route
          path="*"
          element={
            <PlaceholderPage title="Page Not Found" />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}


export default App;