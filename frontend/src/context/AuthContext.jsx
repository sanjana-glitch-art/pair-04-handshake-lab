// Lab 2: authentication state lives in the Redux auth slice. useAuth()
// keeps the Lab 1 interface so existing components did not have to change.
import { useDispatch, useSelector } from "react-redux";
import * as api from "../services/api.js";
import {
  login as loginThunk,
  logout as logoutThunk,
  selectIsAuthenticated,
  selectIsCompany,
  selectIsStudent,
  selectToken,
  selectUserRole,
} from "../store/slices/authSlice.js";

export function AuthProvider({ children }) {
  return children;
}

export function useAuth() {
  const dispatch = useDispatch();
  const token = useSelector(selectToken);
  const userRole = useSelector(selectUserRole);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isStudent = useSelector(selectIsStudent);
  const isCompany = useSelector(selectIsCompany);

  async function login(credentials) {
    const result = await dispatch(loginThunk(credentials));
    if (loginThunk.rejected.match(result)) {
      throw new Error(result.payload || "Sign-in failed.");
    }
    const payload = JSON.parse(atob(result.payload.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return { access_token: result.payload, token_type: "bearer", user_role: payload.role };
  }

  return {
    token,
    userRole,
    isAuthenticated,
    isStudent,
    isCompany,
    login,
    signup: (data) => api.signup(data),
    companySignup: (data) => api.companySignup(data),
    logout: () => dispatch(logoutThunk()),
  };
}
