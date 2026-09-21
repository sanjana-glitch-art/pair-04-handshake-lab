import { createContext, useContext, useState } from "react";
import * as api from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() =>
    localStorage.getItem("access_token")
  );

  async function login(credentials) {
    const data = await api.login(credentials);

    localStorage.setItem("access_token", data.access_token);
    setToken(data.access_token);

    return data;
  }

  async function signup(studentData) {
    return api.signup(studentData);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setToken(null);
  }

  const value = {
    token,
    isAuthenticated: Boolean(token),
    login,
    signup,
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