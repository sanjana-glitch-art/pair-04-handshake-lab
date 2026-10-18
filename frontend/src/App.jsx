import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import StudentLayout from "./layouts/StudentLayout.jsx";
import EmployerLayout from "./layouts/EmployerLayout.jsx";

import StudentDashboard from "./pages/StudentDashboard.jsx";
import StudentProfile from "./pages/StudentProfile.jsx";
import Jobs from "./pages/Jobs.jsx";
import JobDetails from "./pages/JobDetails.jsx";
import Applications from "./pages/Applications.jsx";
import Events from "./pages/Events.jsx";
import RegisteredEvents from "./pages/RegisteredEvents.jsx";
import Preferences from "./pages/Preferences.jsx";
import Assistant from "./pages/Assistant.jsx";
import EmployerDashboard from "./pages/EmployerDashboard.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import RoleProtectedRoute from "./components/RoleProtectedRoute.jsx";
import CompanySignup from "./pages/CompanySignup.jsx";
import EmployerJobs from "./pages/EmployerJobs.jsx";
import EmployerEvents from "./pages/EmployerEvents.jsx";
import EmployerApplications from "./pages/EmployerApplications.jsx";
import EmployerProfile from "./pages/EmployerProfile.jsx";

function PlaceholderPage({ title }) {
  return (
    <div className="container py-5">
      <h2>{title}</h2>

      <p className="text-muted">
        This feature will be implemented next.
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
              to="/login"
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

        <Route
          path="/company-signup"
          element={ <CompanySignup />}
        />

        {/* Student routes */}
        <Route
          element={
            <RoleProtectedRoute role="student" />
          }
        >
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
              element={<Jobs />}
            />

            <Route
              path="jobs/:jobId"
              element={<JobDetails />}
            />

            <Route
              path="applications"
              element={<Applications />}
            />

            <Route
              path="events"
              element={<Events />}
            />

            <Route
              path="registered-events"
              element={<RegisteredEvents />}
            />

            <Route
              path="preferences"
              element={<Preferences />}
            />

            <Route
              path="students"
              element={
                <PlaceholderPage
                  title="Browse Students"
                />
              }
            />

            <Route
              path="assistant"
              element={<Assistant />}
            />
          </Route>
        </Route>

        {/* Employer routes */}
        <Route
          element={
            <RoleProtectedRoute role="company" />
          }
        >
          <Route
            path="/employer"
            element={<EmployerLayout />}
          >
            <Route
              path="dashboard"
              element={<EmployerDashboard />}
            />

            <Route
              path="jobs"
              element={<EmployerJobs />}
            />

            <Route
              path="events"
              element={<EmployerEvents />}
            />

            <Route
              path="profile"
              element={<EmployerProfile />}
            />

            <Route
              path="events"
              element={
                <PlaceholderPage
                  title="Manage Events"
                />
              }
            />

            <Route
              path="applications"
              element={<EmployerApplications />}
            />
          </Route>
        </Route>

        <Route
          path="*"
          element={
            <PlaceholderPage
              title="Page Not Found"
            />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;