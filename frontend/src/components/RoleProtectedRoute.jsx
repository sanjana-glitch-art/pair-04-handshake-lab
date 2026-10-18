import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function RoleProtectedRoute({ role }) {
  const {
    isAuthenticated,
    userRole,
  } = useAuth();

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  if (role && userRole !== role) {
    if (userRole === "company") {
      return (
        <Navigate
          to="/employer/dashboard"
          replace
        />
      );
    }

    return (
      <Navigate
        to="/student/dashboard"
        replace
      />
    );
  }

  return <Outlet />;
}

export default RoleProtectedRoute;