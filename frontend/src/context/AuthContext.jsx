import { createContext, useContext, useState } from "react";
import * as api from "../services/api.js";

const AuthContext = createContext(null);

function getRoleFromToken(token) {
  if (!token) {
    return null;
  }

  try {
    const payload = token.split(".")[1];

    const decodedPayload = JSON.parse(
      atob(
        payload
          .replace(/-/g, "+")
          .replace(/_/g, "/")
      )
    );

    return (
      decodedPayload.role ||
      decodedPayload.user_role ||
      null
    );
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() =>
    localStorage.getItem("access_token")
  );

  const [userRole, setUserRole] = useState(() =>
    getRoleFromToken(
      localStorage.getItem("access_token")
    )
  );

  async function login(credentials) {
    const data = await api.login(credentials);

    const role = getRoleFromToken(data.access_token);

    localStorage.setItem(
      "access_token",
      data.access_token
    );

    setToken(data.access_token);
    setUserRole(role);

    return {
      ...data,
      user_role: role,
    };
  }

  async function signup(studentData) {
    return api.signup(studentData);
  }

  async function companySignup(companyData) {
    return api.companySignup(companyData);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setToken(null);
    setUserRole(null);
  }

  const value = {
    token,
    userRole,
    isAuthenticated: Boolean(token),
    isStudent: userRole === "student",
    isCompany: userRole === "company",
    login,
    signup,
    companySignup,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}